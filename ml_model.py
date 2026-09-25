from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


# ---------------- TRAINING DATA ----------------

food = [
    "pizza", "burger", "restaurant food", "lunch",
    "dinner", "breakfast", "khana", "food",
    "grocery", "groceries", "milk", "vegetables",
    "fruits", "swiggy", "zomato"
]

travel = [
    "uber ride", "ola cab", "cab", "taxi",
    "metro ticket", "bus ticket", "train ticket",
    "flight", "petrol", "diesel", "travel",
    "auto", "rickshaw"
]

shopping = [
    "shirt", "shoes", "clothes", "shopping",
    "amazon order", "flipkart order", "jeans",
    "tshirt", "jacket", "watch", "bag"
]

education = [
    "book", "notebook", "college fees", "education",
    "course", "pen", "school", "college", "exam",
    "stationery", "study material"
]

entertainment = [
    "movie", "cinema", "video game", "netflix",
    "concert", "entertainment", "music", "spotify",
    "game", "gaming"
]

bills = [
    "electricity bill", "electricity", "water bill",
    "water", "internet bill", "wifi bill",
    "mobile recharge", "phone recharge",
    "recharge", "telephone"
]

health = [
    "medicine", "doctor", "hospital", "medical",
    "pharmacy", "health checkup"
]

other = [
    "gift", "donation", "miscellaneous", "other expense"
]


# ---------------- PREPARE DATA ----------------

descriptions = (
    food +
    travel +
    shopping +
    education +
    entertainment +
    bills +
    health +
    other
)

categories = (
    ["Food"] * len(food) +
    ["Travel"] * len(travel) +
    ["Shopping"] * len(shopping) +
    ["Education"] * len(education) +
    ["Entertainment"] * len(entertainment) +
    ["Bills"] * len(bills) +
    ["Health"] * len(health) +
    ["Other"] * len(other)
)


# ---------------- AI MODEL ----------------

vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    lowercase=True
)

X = vectorizer.fit_transform(descriptions)

model = LogisticRegression(
    max_iter=1000
)

model.fit(X, categories)


# ---------------- PREDICTION FUNCTION ----------------

def predict_category(description):

    description = description.strip().lower()

    if not description:
        return "Other"

    text_vector = vectorizer.transform(
        [description]
    )

    prediction = model.predict(
        text_vector
    )

    return prediction[0]