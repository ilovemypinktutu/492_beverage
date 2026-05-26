
import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib

# Replace with your uploaded data path
df = pd.read_excel("sales_marketing_Coca-Cola.xlsx")

# Example columns
X = df[
    [
        "price",
        "advertising",
        "competitor_price",
        "competitor_ad"
    ]
]

y = df["quantity"]

model = LinearRegression()
model.fit(X, y)

joblib.dump(model, "models/demand_model.pkl")

print("Model saved.")
