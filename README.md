🧾 Smart Khata – Voice & AI-Powered Udhaar Management System

Smart Khata is an intelligent Udhaar (debt) management system designed to simplify daily shopkeeping operations. It allows voice and text-based entries and provides real-time retrieval and visualization of customer debts using Firebase and AI-powered prompt-tuned extraction.

🚀 Key Features
🎙️ Voice Input with AI Extraction

Record Udhaar transactions in Hindi or English.

Uses Google Speech Recognition + Gemini AI prompt-tuning to extract customer_name, item, amount, and transaction type.

Automatically converts spoken sentences like "500 ka chawal liya Ram ne" to structured JSON.

📝 Manual Entry

Add transactions via a form when voice input is not preferred.

Ensures all Udhaar records are captured consistently.

📂 Firebase Integration

Securely stores and syncs real-time data.

Supports both automatic AI-extracted entries and manual entries.

🔍 Quick Retrieval

Search a customer’s name to instantly see credit/debt history.

Displays Udhaar, Paid, and Net Balance details.

📊 Visualization Dashboard

Total Udhaar per Customer (Bar Chart)

Udhaar Over Time (Line Chart)

Helps shopkeepers identify peak Udhaar days, customer trends, and manage credit efficiently.

💡 Real-Life Problem Solved

Tracking Udhaar manually can lead to forgotten or misplaced entries, especially in busy shops. Smart Khata ensures:

Quick voice-based entry

Automatic AI parsing of transactions

Real-time storage & retrieval

Visual insights for better business decisions

🛠️ Tech Stack
Technology	Purpose
Streamlit	Web UI & Deployment
Google Speech Recognition API	Convert Hindi/English voice to text
Gemini AI (Prompt-Tuned)	Extract structured data from text
Firebase Realtime Database	Store & retrieve customer data
Python	Core logic, backend, and integration
Plotly Express	Data visualization for Udhaar trends
🤝 Future Enhancements

Dashboard Analytics: Power BI or advanced Plotly insights.

Automated SMS Reminders: Notify customers of outstanding Udhaar.

Trend Analysis with GenAI: Summarize Udhaar patterns and generate actionable insights.

🙌 Acknowledgements

Inspired by real shopkeeping experience where manual Udhaar tracking caused issues.

Uses Google Speech API, Gemini AI, Firebase, and Streamlit to make voice-enabled Udhaar management accessible for local businesses.
