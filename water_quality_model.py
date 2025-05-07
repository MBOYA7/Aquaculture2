import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt

# Load the dataset
df = pd.read_csv('WQD_selected.csv')  

# Features and target
X = df[['Temp', 'Turbidity', 'pH']]
y = df['Water Quality']

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

#  Train the model FIRST
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)  # Now clf is defined and trained

# Then make predictions
y_pred = clf.predict(X_test)

# Evaluate
print(classification_report(y_test, y_pred))

import joblib

# Save the trained model to a .pkl file
joblib.dump(clf, 'water_quality_model.pkl')
print("✅ Model saved as water_quality_model.pkl")

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['Excellent', 'Good', 'Poor'],
            yticklabels=['Excellent', 'Good', 'Poor'])
plt.xlabel('Predicted')
plt.ylabel('Actual')
plt.title('Confusion Matrix')
plt.show()




