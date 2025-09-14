from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import torch
from transformers import RobertaForSequenceClassification, RobertaTokenizer

app = FastAPI()

device = torch.device("cpu")
model_path = "hetbhalani/roberta-enhanced-for-sentiment"

model = RobertaForSequenceClassification.from_pretrained(model_path)
model.eval()
tokenizer = RobertaTokenizer.from_pretrained(model_path)
model.to(device)

#pydantic model to get the list of movie reviews
class MovieReviews(BaseModel):
    reviews: List[str]

@app.post('/predict')
def sentiment_model_predict(movie_reviews: MovieReviews):
    texts = movie_reviews.reviews
    inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=128)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        preds = outputs.logits.argmax(-1).tolist()

    label_map = {0: "Negative", 1: "Neutral", 2: "Positive"}
    pred_list = [label_map[p] for p in preds]

    return {"sentiments": pred_list}
