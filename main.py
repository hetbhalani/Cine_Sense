from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
import json
import time

BACKEND_URL = "https://hetbhalani-movie-sentiment-fastapi.hf.space/predict"

st.set_page_config(
    page_title="Movie Sentiment Analysis",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 Movie Sentiment Analysis")
st.markdown("---")

#movie input
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    movie_name = st.text_input("🔍 Enter a movie name", placeholder="e.g., The Dark Knight")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

#idk
def get_chrome_options():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  
    chrome_options.add_argument("--no-sandbox")  
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")  
    return chrome_options

#movie url for id
def get_movie_url(movie_name):
    search_url = f"https://www.imdb.com/find?q={movie_name}&s=tt"
    try:
        search_response = requests.get(search_url, headers=headers, timeout=10)
        search_response.raise_for_status()
        search_soup = BeautifulSoup(search_response.text, "html.parser")
        
        #multiple selectors if anyone fails
        selectors = [
            "a.ipc-metadata-list-summary-item__t",
            "a[href*='/title/tt']",
            ".findResult .result_text a"
        ]
        
        movie_link_tag = None
        for selector in selectors:
            movie_link_tag = search_soup.select_one(selector)
            if movie_link_tag:
                break
        
        #here we get the movie id to make full url
        if movie_link_tag:
            movie_link = movie_link_tag['href']
            movie_id = movie_link.split('/')[2]
            print(f"Movie ID: {movie_id}")
            return movie_id
        else:
            print("Movie not found!")
            return None
            
    except Exception as e:
        print(f"Error searching for movie: {e}")
        return None

#this is for showing poster
def get_movie_poster(movie_id):
    movie_page_url = f"https://www.imdb.com/title/{movie_id}/"
    
    try:
        response = requests.get(movie_page_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        #multiple selectors if anyone fails
        poster_selectors = [
            "img.ipc-image",
            "img[class*='poster']",
            "div.ipc-media img",
            "img.ipc-lockup-overlay__screen",
            "div.ipc-poster img",
            ".poster img",
            "[data-testid='hero-media__poster'] img"
        ]
        
        for selector in poster_selectors:
            poster_tag = soup.select_one(selector)
            if poster_tag and poster_tag.get('src'):
                poster_url = poster_tag['src']
                print(f"Found poster using selector: {selector}")
                return poster_url
        
        print("No poster found with any selector")
        return None
        
    except Exception as e:
        print(f"Error getting poster: {e}")
        return None

#click the show all button to get more reviews
def click_show_all_button(driver, max_clicks=2):
    clicks = 0
    wait = WebDriverWait(driver, 5)
    
    button_selectors = [
        "//button[contains(@class, 'ipc-see-more__button')]",
        "//button[contains(text(), 'Show All')]",
        "//button[contains(text(), 'Load More')]",
        "//span[contains(text(), 'Show All')]/parent::button",
        "//div[contains(@class, 'load-more')]//button"
    ]
    
    while clicks < max_clicks:
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            button_found = False
            for selector in button_selectors:
                try:
                    print(f"Looking for button with selector: {selector}")
                    button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    
                    if button and button.is_displayed():
                        print(f"Found button with selector: {selector}")
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(1)
                        
                        try:
                            driver.execute_script("arguments[0].click();", button)
                        except:
                            button.click()
                        
                        clicks += 1
                        print(f"Clicked button {clicks} time(s)")
                        time.sleep(3)
                        button_found = True
                        break
                        
                except (TimeoutException, NoSuchElementException):
                    continue
            
            if not button_found:
                print("No more buttons to click")
                break
                
        except Exception as e:
            print(f"Error clicking button: {str(e)}")
            break
    
    return clicks

#scrap reviews
def get_reviews(movie_name):
    movie_id = get_movie_url(movie_name)
    if not movie_id:
        return [], None
    
    #this is the url set for date modified reviews
    reviews_url = f"https://www.imdb.com/title/{movie_id}/reviews/?ref_=tt_ururv_genai_sm&sort=submission_date%2Cdesc"
    
    chrome_options = get_chrome_options()
    driver = None
    
    try:
        print("Initializing Chrome driver...")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        
        print(f"Loading reviews page: {reviews_url}")
        driver.get(reviews_url)
        time.sleep(5)
        
        total_clicks = click_show_all_button(driver, max_clicks=2)
        print(f"Total buttons clicked: {total_clicks}")
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        page_source = driver.page_source
        
    except Exception as e:
        print(f"Error during scraping: {e}")
        return [], None
        
    finally:
        if driver:
            try:
                driver.quit()
                print("Browser closed successfully.")
            except:
                print("Error closing browser.")
    
    soup = BeautifulSoup(page_source, "html.parser")
    reviews = []
    
    #multiple selectors if anyone fails
    review_selectors = [
        "div.ipc-html-content-inner-div",
        "div.content .text",
        "div[data-testid='review-content']",
        ".review-container .content"
    ]
    
    #scraping reviews one by one
    for selector in review_selectors:
        review_elements = soup.select(selector)
        if review_elements:
            print(f"Found {len(review_elements)} reviews with selector: {selector}")
            for review in review_elements:
                text = review.get_text(strip=True)
                if text and len(text) > 20:
                    reviews.append(text)
            break
    
    poster_url = get_movie_poster(movie_id)
    
    return reviews, poster_url


################################ Streamlit ###################################
if movie_name:
    print(f"Scraping reviews for: {movie_name}")
    
    with st.spinner("🔄 Scraping movie reviews and poster..."):
        movie_reviews, poster_url = get_reviews(movie_name)

    if movie_reviews:
        print(f"\nTotal reviews scraped: {len(movie_reviews)}")
        
        st.markdown("---")
        
        st.subheader(f"🎭 {movie_name}")
        poster_col1, poster_col2, poster_col3 = st.columns([1, 1, 1])
        with poster_col2:
            if poster_url:
                st.image(poster_url, width=300, caption=f"{movie_name}")
            else:
                st.warning("⚠️ Could not retrieve movie poster")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📊 Total Reviews Scraped", len(movie_reviews))
        
        if len(movie_reviews) > 0:
            st.subheader("🎯 Sentiment Analysis Results")
            
            with st.spinner("🧠 Analyzing sentiments..."):
                #data to send to FastAPI
                data = {"reviews": movie_reviews}

                try:
                    #POST request
                    response = requests.post(BACKEND_URL, json=data)
                    response.raise_for_status()
                    #parsing
                    sentiment_results = response.json()["sentiments"]
                    
                    #sentiment counts
                    sentiment_counts = {sentiment: sentiment_results.count(sentiment) for sentiment in ["Positive", "Neutral", "Negative"]}
                    total_reviews = len(sentiment_results)
                    
                except requests.exceptions.RequestException as e:
                    st.error(f"Error fetching sentiment results: {e}")
                    st.stop()
            
            stars = ((sentiment_counts['Positive'] * 10) + (sentiment_counts['Neutral'] * 5) + (sentiment_counts['Negative'] * 3)) / total_reviews
            # tabs for different views
            tab1, tab2, tab3 = st.tabs(["📊 Overview", "📈 Charts", "📝 Reviews"])
            
            #overview Tab
            with tab1:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("✅ Positive", sentiment_counts["Positive"], 
                            f"{sentiment_counts['Positive']/total_reviews*100:.1f}%")
                with col2:
                    st.metric("😐 Neutral", sentiment_counts["Neutral"], 
                            f"{sentiment_counts['Neutral']/total_reviews*100:.1f}%")
                with col3:
                    st.metric("❌ Negative", sentiment_counts["Negative"], 
                            f"{sentiment_counts['Negative']/total_reviews*100:.1f}%")
                with col4:
                    if sentiment_counts["Positive"] > sentiment_counts["Negative"]:
                        overall = "😊 Mostly Positive"
                    elif sentiment_counts["Negative"] > sentiment_counts["Positive"]:
                        overall = "😞 Mostly Negative"
                    else:
                        overall = "😐 Mixed"
                    st.metric("🎯 Overall", overall)

                st.markdown("---")
                st.subheader("⭐ Star Rating")
                st.write(f"**Estimated Stars**: {round(stars, 1)} / 10")
                
                star_rating = round(stars)
                star_icons = "⭐" * star_rating + "☆" * (10 - star_rating)
                st.markdown(f"<h3 style='text-align: center;'>{star_icons}</h3>", unsafe_allow_html=True)
            
            with tab2:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Pie chart
                    df_pie = pd.DataFrame({
                        'Sentiment': list(sentiment_counts.keys()),
                        'Count': list(sentiment_counts.values())
                    })
                    
                    fig_pie = px.pie(df_pie, values='Count', names='Sentiment', 
                                    title="Sentiment Distribution",
                                    color_discrete_map={
                                        'Positive': '#28a745',
                                        'Neutral': '#ffc107', 
                                        'Negative': '#dc3545'
                                    })
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    # Bar chart
                    fig_bar = px.bar(df_pie, x='Sentiment', y='Count',
                                    title="Sentiment Count",
                                    color='Sentiment',
                                    color_discrete_map={
                                        'Positive': '#28a745',
                                        'Neutral': '#ffc107', 
                                        'Negative': '#dc3545'
                                    })
                    fig_bar.update_layout(showlegend=False)
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                fig_horizontal = go.Figure(data=[
                    go.Bar(name='Sentiment Distribution', 
                          x=list(sentiment_counts.values()), 
                          y=list(sentiment_counts.keys()),
                          orientation='h',
                          marker_color=['#28a745', '#ffc107','#dc3545'])
                ])
                fig_horizontal.update_layout(
                    title="Detailed Sentiment Breakdown",
                    xaxis_title="Number of Reviews",
                    yaxis_title="Sentiment",
                    showlegend=False
                )
                st.plotly_chart(fig_horizontal, use_container_width=True)
            
            with tab3:
                show_all = st.checkbox("Show all reviews", value=False)

                # Combine reviews with their predicted sentiment
                filtered_reviews = list(zip(movie_reviews, sentiment_results))
                display_count = len(filtered_reviews) if show_all else min(10, len(filtered_reviews))

                st.write(f"Showing {display_count} out of {len(filtered_reviews)} reviews")

                for idx in range(display_count):
                    review, sentiment = filtered_reviews[idx]

                    rev_col1, rev_col2 = st.columns([4, 1])

                    with rev_col1:
                        if sentiment == "Positive":
                            st.success(f"**Review {idx+1}**")
                        elif sentiment == "Negative":
                            st.error(f"**Review {idx+1}**")
                        else:
                            st.info(f"**Review {idx+1}**")

                    with rev_col2:
                        if sentiment == "Positive":
                            st.success(f"✅ {sentiment}")
                        elif sentiment == "Negative":
                            st.error(f"❌ {sentiment}")
                        else: 
                            st.info(f"😐 {sentiment}")

                    with st.expander("📖 Read Full Review"):
                        st.write(review)

                if not show_all and len(filtered_reviews) > 10:
                    st.info(f"💡 Showing 10 out of {len(filtered_reviews)} reviews. Check 'Show all reviews' to see more.")
                
        
    else:
        st.error("❌ No reviews found for this movie. Please check the movie name and try again.")
        st.info("💡 Try using the exact movie title or a popular movie name.")
        
else:
    st.info("👋 Welcome! Enter a movie name above to get started.")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.markdown("""
        ### 🚀 How to use:
        1. **Enter a movie name** in the search box above
        2. **Wait for scraping** (30-60 seconds)
        3. **View results** in organized tabs
        4. **Explore charts** and individual reviews
        """)
    
    with info_col2:
        st.markdown("""
        ### ✨ Features:
        - 🎭 **Movie poster** display
        - 📊 **Sentiment metrics** and percentages
        - 📈 **Interactive charts** (pie, bar, horizontal)
        - 📝 **Filterable reviews** by sentiment
        - 🎯 **Overall sentiment** assessment
        """)
    
    st.markdown("---")
    st.markdown("**Note:** The scraping process may take 30-60 seconds depending on the number of reviews available.")