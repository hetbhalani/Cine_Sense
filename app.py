from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import torch
from transformers import RobertaForSequenceClassification, RobertaTokenizer

app = FastAPI()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_path = "./model"
model = RobertaForSequenceClassification.from_pretrained(model_path)
tokenizer = RobertaTokenizer.from_pretrained(model_path)
model.to(device)

#pydantic model to get the list of movie reviews
class MovieReviews(BaseModel):
    reviews: List[str]

@app.post('/predict')
def sentiment_model_predict(movie_reviews: MovieReviews):
    pred_list = []

    for i, text in enumerate(movie_reviews.reviews):        
        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=128)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)

        pred = outputs.logits.argmax(-1).item()
        label_map = {0: "Negative", 1: "Neutral", 2: "Positive"}
        pred_list.append(label_map[pred])

    return {"sentiments": pred_list}