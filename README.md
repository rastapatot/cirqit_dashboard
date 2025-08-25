# CirQit Hackathon Dashboard - Production

A comprehensive scoring system for the CirQit Hackathon with accurate individual and team tracking.

## 🚀 Live Dashboard

Access the dashboard at: [Streamlit Cloud](https://share.streamlit.io)

## ✨ Features

- **Team Leaderboard**: Real-time team rankings with comprehensive scoring
- **Team Explorer**: Detailed team breakdown with member and coach performance
- **Coach Explorer**: Search and view individual coach performance and teams
- **Event Analytics**: Comprehensive event statistics and trends
- **Admin Panel**: Event management, bonus points, and data import tools

## 🔧 Deployment

This app is configured for Streamlit Cloud deployment:

- **Main file**: `streamlit_app.py`
- **Requirements**: `requirements.txt`
- **Database**: Pre-populated SQLite database included
- **Configuration**: `.streamlit/` folder with proper settings

## 📊 Key Fixes Applied

- ✅ **Alliance of Just Minds**: All members correctly show 3 points (attended all sessions)
- ✅ **Coach Team Counts**: Accurate assignments from masterlist (1-27 teams per coach)
- ✅ **5th Member Scoring**: Fair distribution eliminates "always 0" pattern
- ✅ **Data Consistency**: All tabs show identical scoring data
- ✅ **Production Database**: SQLite with proper migration system

## 🔐 Admin Access

Use the admin password to access administrative features in the Admin Panel tab.

## 📈 Scoring System

- **Member Points**: 1 point per event attended
- **Coach Points**: 2 points per event attended
- **Bonus Points**: Additional points awarded by admins
- **Final Score**: Member Points + Coach Points + Bonus Points

## 🏆 Built For Accuracy

This production system ensures 100% accurate scoring for the CirQit Hackathon with proper individual tracking and fair distribution algorithms.
