import streamlit as st
from pymongo import MongoClient
from textblob import TextBlob
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import csv
from io import StringIO
import requests

# MongoDB connection setup
client = MongoClient("mongodb://localhost:27017/")
db = client["movie_reviews_db"]
reviews_collection = db["reviews"]

# TMDb API setup
TMDB_API_KEY = "fb60ea478c32856c45015ed39cbd23c0"  # Replace with your TMDb API key
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Function to analyze sentiment
def analyze_sentiment(review_text):
    blob = TextBlob(review_text)
    polarity = blob.sentiment.polarity
    if polarity > 0:
        return "Positive"
    elif polarity < 0:
        return "Negative"
    else:
        return "Neutral"

# Function to get movie recommendations
def get_movie_recommendations(movie_title):
    search_url = f"{TMDB_BASE_URL}/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": movie_title
    }
    response = requests.get(search_url, params=params)
    results = response.json().get("results", [])

    recommendations = []
    if results:
        # Get the first search result's ID for recommendations
        movie_id = results[0]["id"]
        recommendations_url = f"{TMDB_BASE_URL}/movie/{movie_id}/recommendations"
        recommendations_response = requests.get(recommendations_url, params={"api_key": TMDB_API_KEY})
        recommendations = recommendations_response.json().get("results", [])
    
    return recommendations

# Streamlit UI
st.title("Movie Review Submission")

# Initialize session state for inputs
if 'username' not in st.session_state:
    st.session_state.username = ''
if 'movie_title' not in st.session_state:
    st.session_state.movie_title = ''
if 'review' not in st.session_state:
    st.session_state.review = ''

# Input form for user feedback
st.session_state.username = st.text_input("Your Name", value=st.session_state.username)
st.session_state.movie_title = st.text_input("Movie Title", value=st.session_state.movie_title)
st.session_state.review = st.text_area("Your Review", value=st.session_state.review)

if st.button("Submit"):
    username = st.session_state.username.strip()
    movie_title = st.session_state.movie_title.strip()
    review = st.session_state.review.strip()

    if username and movie_title and review:
        # Analyze sentiment
        sentiment = analyze_sentiment(review)
        
        # Store the review in MongoDB
        review_data = {
            "username": username,
            "movie_title": movie_title,
            "review": review,
            "sentiment": sentiment,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        reviews_collection.insert_one(review_data)
        st.success("Review submitted successfully!")

        # Get movie recommendations
        recommendations = get_movie_recommendations(movie_title)

        if recommendations:
            st.header("Recommended Movies")
            for movie in recommendations:
                st.subheader(movie["title"])
                st.write(f"Release Date: {movie['release_date']}")
                st.write(f"Overview: {movie['overview']}")
                st.write(f"[More Info](https://www.themoviedb.org/movie/{movie['id']})")
                st.write("---")
        else:
            st.warning("No recommendations found.")

        # Optionally, clear the inputs after submission
        st.session_state.username = ''
        st.session_state.movie_title = ''
        st.session_state.review = ''
    else:
        st.error("Please provide username, movie title, and review.")

# Display all reviews
st.header("Submitted Reviews")
reviews_list = list(reviews_collection.find({}))

if reviews_list:
    for review in reviews_list:
        st.subheader(f"{review['username']} - {review['movie_title']}")
        st.write(review['review'])
        st.write(f"Sentiment: {review['sentiment']}")
        st.write(f"Submitted on: {review['timestamp']}")
        st.write("---")
else:
    st.info("No reviews submitted yet.")

# Search Reviews by Keyword
st.header("Search Reviews")
search_query = st.text_input("Enter a keyword to search reviews:")

if search_query:
    search_results = reviews_collection.find({"review": {"$regex": search_query, "$options": "i"}})
    st.write(f"Showing results for '{search_query}':")

    for review in search_results:
        st.subheader(f"{review['username']} - {review['movie_title']}")
        st.write(review['review'])
        st.write(f"Sentiment: {review['sentiment']}")
        st.write(f"Submitted on: {review['timestamp']}")
        st.write("---")
else:
    st.info("Enter a keyword to search reviews.")

# Sentiment Distribution Visualization
st.header("Sentiment Distribution")
positive_count = reviews_collection.count_documents({"sentiment": "Positive"})
neutral_count = reviews_collection.count_documents({"sentiment": "Neutral"})
negative_count = reviews_collection.count_documents({"sentiment": "Negative"})

if positive_count or neutral_count or negative_count:
    sentiments = ["Positive", "Neutral", "Negative"]
    counts = [positive_count, neutral_count, negative_count]

    fig, ax = plt.subplots()
    ax.pie(counts, labels=sentiments, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    st.pyplot(fig)
else:
    st.info("No feedback data available for sentiment distribution.")

# Export Reviews to CSV
st.header("Export Reviews")

if st.button("Export to CSV"):
    reviews = list(reviews_collection.find({}, {"_id": 0}))

    if reviews:
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=reviews[0].keys())
        writer.writeheader()
        writer.writerows(reviews)

        st.download_button(
            label="Download CSV",
            data=output.getvalue(),
            file_name='reviews.csv',
            mime='text/csv'
        )
    else:
        st.info("No reviews to export.")

# Option to delete all reviews
if st.button("Delete All Reviews"):
    reviews_collection.delete_many({})
    st.warning("All reviews deleted.")
