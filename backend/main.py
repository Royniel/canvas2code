import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "success", "message": "canvas2code AI backend is live!"}

# Notice we added `framework: str = Form(...)` here!
@app.post("/generate")
async def generate_code(file: UploadFile = File(...), framework: str = Form(...)):
    try:
        image_bytes = await file.read()
        
        # We use an f-string (f"") to inject their framework choice into the prompt
        prompt = f"""
        You are an expert frontend developer. Look at this uploaded sketch or wireframe.
        Write a complete, working {framework} component using Tailwind CSS that perfectly matches the sketch.
        Make it look modern and professional.
        Return ONLY the raw code, ready to be rendered. Do not include markdown formatting like ```javascript.
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type=file.content_type)
            ]
        )
        
        return {"status": "success", "code": response.text}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}