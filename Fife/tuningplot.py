import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data from CSV
csv_file = 'tuning.csv'
df = pd.read_csv(csv_file)

# Plotting the frequencies
plt.figure(figsize=(10, 6))
# Columns to exclude from plotting
exclude_columns = ['Expected_Note', 'Expected_Frequency']

# Calculate difference in cents and plot dynamically
for col_name in df.columns:
    if col_name not in exclude_columns:
        cents_diff = 1200 * np.log2(df[col_name] / df['Expected_Frequency'])
        plt.plot(df['Expected_Note'], cents_diff, marker='o', linestyle='--', label=f'{col_name.replace("_", " ")} Cents Diff')

# Add labels and legend
plt.xlabel('Expected Note')
plt.ylabel('Difference (Cents)')
plt.title('Difference from Expected Frequency in Cents')
plt.axhline(0, color='gray', linestyle='--')
plt.legend()
plt.grid(True)
plt.show()