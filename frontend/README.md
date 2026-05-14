# 🎨 Canvas2Code

![Next.js](https://img.shields.io/badge/Next.js-Black?style=for-the-badge&logo=next.js&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=FastAPI&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)

Canvas2Code is an AI-powered full-stack application that bridges the gap between design and development. By leveraging Google's Gemini Vision models, it instantly translates hand-drawn UI sketches, wireframes, or screenshots into production-ready frontend code.

## ✨ Features

* **Vision-to-Code Generation:** Upload any UI image and receive fully functional UI components within seconds.
* **Multi-Framework Support:** Dynamically generate code for **React (Next.js)**, **Vue 3**, or **Vanilla HTML/CSS** via a user-friendly interface.
* **Modern UI/UX:** Built with a dark-mode Next.js frontend featuring custom CSS loading animations and responsive design.
* **One-Click Copy:** Seamlessly extract generated code using the native clipboard API with visual feedback.
* **High-Performance Backend:** Powered by Python and FastAPI, ensuring rapid processing and asynchronous image handling.

## 🛠️ Tech Stack

**Frontend:**
* Next.js (React)
* TypeScript
* Tailwind CSS

**Backend:**
* Python
* FastAPI
* Google GenAI SDK (`google-genai`)
* Uvicorn (ASGI Server)

---

## 🚀 Getting Started (Local Development)

Follow these steps to run Canvas2Code on your local machine.

### Prerequisites
* Node.js (v18+)
* Python (3.9+)
* A free [Google Gemini API Key](https://aistudio.google.com/)

### 1. Clone the Repository
```bash
git clone [https://github.com/YOUR_USERNAME/canvas2code.git](https://github.com/YOUR_USERNAME/canvas2code.git)
cd canvas2code

# Backend Setup (FastAPI)

cd backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env

👨‍💻 Author
Nilanjan Roy

Fullstack Application Developer

* [LinkedIn](https://www.linkedin.com/in/royniel) | [GitHub](https://github.com/royniel)