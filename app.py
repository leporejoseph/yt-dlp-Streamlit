import streamlit as st
import asyncio
from yt_dlp import YoutubeDL
from streamlit_player import st_player
import aiohttp
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import json
import os
import datetime

# Initialize session state
if 'current_video' not in st.session_state:
    st.session_state.current_video = None
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'saved_videos' not in st.session_state:
    st.session_state.saved_videos = []

SAVED_VIDEOS_FILE = 'saved_videos.json'

# Helper functions
async def fetch_data(url, session):
    async with session.get(url) as response:
        return await response.read()

def load_saved_videos():
    if os.path.exists(SAVED_VIDEOS_FILE):
        with open(SAVED_VIDEOS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_videos_to_file():
    with open(SAVED_VIDEOS_FILE, 'w') as f:
        json.dump(st.session_state.saved_videos, f)

def create_thumbnail_with_overlay(thumbnail_bytes, title, duration):
    try:
        img = Image.open(io.BytesIO(thumbnail_bytes)) if thumbnail_bytes else Image.new('RGB', (320, 180), color=(200, 200, 200))
        draw = ImageDraw.Draw(img)
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 100))
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        font = ImageFont.truetype("arial.ttf", 20)
        draw = ImageDraw.Draw(img)
        draw.text((10, img.size[1] - 40), title[:50] + '...' if len(title) > 50 else title, font=font, fill=(255, 255, 255))
        draw.text((img.size[0] - 70, 10), str(datetime.timedelta(seconds=duration)), font=font, fill=(255, 255, 255))
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        st.warning(f"Failed to create thumbnail overlay: {str(e)}")
        return None

async def search_videos(query):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'extract_flat': 'in_playlist',
            'force_generic_extractor': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"ytsearch10:{query}", download=False)
        
        videos = []
        for video in search_results.get('entries', []):
            videos.append({
                'id': video.get('id', 'N/A'),
                'title': video.get('title', 'No Title'),
                'thumbnail': video.get('thumbnail', video.get('thumbnails', [{'url': ''}])[0].get('url', '')),
                'duration': video.get('duration'),
                'description': video.get('description', 'No description available')
            })
        return videos
    except Exception as e:
        st.error(f"An error occurred while searching for videos: {str(e)}")
        return []

async def get_video_info(video_id):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

def display_video_player(video):
    video_url = f"https://www.youtube.com/watch?v={video['id']}"
    st_player(video_url, key="youtube_player", playing=True)

def display_video_details(video_info):
    try:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write(f"## {video_info.get('title', 'No Title')}")
            
            # Add Save Video and Remove Video buttons
            col1_1, col1_2 = st.columns(2)
            with col1_1:
                if st.button("Save Video"):
                    save_video(st.session_state.current_video)
            with col1_2:
                if st.session_state.current_video in st.session_state.saved_videos:
                    if st.button("Remove from Saved"):
                        remove_saved_video(st.session_state.current_video)
                        st.rerun()
            
            st.write(f"**Channel:** {video_info.get('channel', 'Unknown')}")
            upload_date = video_info.get('upload_date')
            if upload_date:
                upload_date = datetime.datetime.strptime(upload_date, '%Y%m%d')
                st.write(f"**Published:** {upload_date.strftime('%m/%d/%Y')}")
            st.write(f"**Views:** {video_info.get('view_count', 'Unknown'):,}")
            
            if 'like_count' in video_info:
                st.write(f"**Likes:** {video_info['like_count']:,}")
            
            st.write("### Description")
            st.write(video_info.get('description', 'No description available'))
        
        with col2:
            st.write("### Video Details")
            duration = video_info.get('duration')
            if duration:
                st.write(f"**Duration:** {str(datetime.timedelta(seconds=duration))}")
            st.write(f"**Category:** {video_info.get('category', 'N/A')}")
            
            tags = video_info.get('tags', [])
            if tags:
                st.write("**Tags:**")
                st.write(", ".join(tags[:10]))  # Display first 10 tags
            
            chapters = video_info.get('chapters', [])
            if chapters:
                st.write("### Chapters")
                for chapter in chapters:
                    st.write(f"- [{chapter.get('start_time', 'Unknown')}] {chapter.get('title', 'Untitled')}")
        
        st.write("### Social Media")
        if 'channel_url' in video_info:
            st.write(f"[YouTube Channel]({video_info['channel_url']})")
        
        if st.button("Return to Search Results"):
            st.session_state.current_video = None
            st.rerun()
    
    except Exception as e:
        st.error(f"An error occurred while displaying video details: {str(e)}")

def save_video(video):
    if video not in st.session_state.saved_videos:
        st.session_state.saved_videos.append(video)
        save_videos_to_file()
        st.toast(f"Video '{video['title']}' has been saved.")
    else:
        st.warning("This video is already saved.")

def remove_saved_video(video):
    st.session_state.saved_videos = [v for v in st.session_state.saved_videos if v['id'] != video['id']]
    save_videos_to_file()
    st.toast(f"Video '{video['title']}' has been removed from saved videos.")

async def main():
    st.set_page_config(page_title="Video Explorer", layout="wide")
    
    st.title("Video Explorer")

    # Load saved videos
    st.session_state.saved_videos = load_saved_videos()

    # Sidebar for search input and saved videos
    with st.sidebar:
        st.logo("content/yt-dlp.png")

        # Create a form for the search functionality
        with st.form(key='search_form'):
            search_query = st.text_input("Search for videos:", placeholder="Enter Topic or YouTube URL Here")
            search_button = st.form_submit_button("Search")

        # Move this outside the form to avoid rerunning on every keypress
        if search_button and search_query:
            with st.spinner("Searching for videos..."):
                st.session_state.search_results = await search_videos(search_query)
            st.session_state.current_video = None
            st.rerun()

        with st.expander("Saved Watchlist"):
            if not st.session_state.saved_videos:
                st.write("No saved videos yet.")
            else:
                for video in st.session_state.saved_videos:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(video['title'])
                    with col2:
                        if st.button("Watch", key=f"saved_watch_{video['id']}"):
                            st.session_state.current_video = video
                            st.rerun()

    # Main content area
    main_content = st.empty()

    # Display search results or video player
    if st.session_state.current_video:
        with main_content.container():
            try:
                display_video_player(st.session_state.current_video)
                
                # Fetch detailed video information
                video_info = await get_video_info(st.session_state.current_video['id'])
                display_video_details(video_info)
            except Exception as e:
                st.error(f"An error occurred while displaying the video: {str(e)}")
    else:
        with main_content.container():
            cols = st.columns(5)
            async with aiohttp.ClientSession() as session:
                for i, video in enumerate(st.session_state.search_results):
                    with cols[i % 5]:
                        try:
                            thumbnail = await fetch_data(video['thumbnail'], session)
                            thumbnail_b64 = create_thumbnail_with_overlay(thumbnail, video['title'], video['duration'])
                            st.image(f"data:image/png;base64,{thumbnail_b64}", use_column_width=True)
                            if st.button("Watch", key=f"search_watch_{video['id']}"):
                                st.session_state.current_video = video
                                st.rerun()
                            st.write(f"**{video['title'][:30]}...**")
                            st.write(f"Duration: {str(datetime.timedelta(seconds=video['duration']))}")
                        except Exception as e:
                            st.error(f"Error displaying video: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())