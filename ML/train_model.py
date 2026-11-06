"""Train, evaluate and save the KNN ride-match model (knn_ride_model.joblib)."""
import json, joblib, pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from features import FEATURE_COLUMNS, LABELS

df = pd.read_csv("ride_dataset.csv")
X, y = df[FEATURE_COLUMNS], df["match_label"]
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Scaling matters for KNN because it is distance based.
pipe = Pipeline([("scale", StandardScaler()), ("knn", KNeighborsClassifier())])
grid = GridSearchCV(pipe, {"knn__n_neighbors": [3, 5, 7, 9, 11, 15],
                           "knn__weights": ["uniform", "distance"]}, cv=5, scoring="accuracy")
grid.fit(X_tr, y_tr)
model = grid.best_estimator_

pred = model.predict(X_te)
acc = accuracy_score(y_te, pred)
print("Best params :", grid.best_params_)
print(f"Accuracy    : {acc:.4f}")
print(classification_report(y_te, pred, target_names=LABELS))
print("Confusion matrix:\n", confusion_matrix(y_te, pred))

joblib.dump(model, "knn_ride_model.joblib")
json.dump({"accuracy": round(acc, 4), "best_params": grid.best_params_, "labels": LABELS,
           "features": FEATURE_COLUMNS}, open("model_metrics.json", "w"), indent=2)
print("saved knn_ride_model.joblib")
