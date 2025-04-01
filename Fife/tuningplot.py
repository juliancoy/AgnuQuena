import pandas as pd
import matplotlib.pyplot as plt

# Load data from CSV
csv_file = 'tuning.csv'
df = pd.read_csv(csv_file)

# Plotting the frequencies
plt.figure(figsize=(10, 6))

# Plot Expected Frequency
plt.plot(df['Expected_Note'], df['Expected_Frequency'], marker='o', label='Expected Frequency')

# Plot Actual Frequency (Stock In, 1.5cm)
plt.plot(df['Expected_Note'], df['Actual_Frequency_StockIn_1_5cm'], marker='o', linestyle='--', label='Actual Frequency (Stock In, 1.5cm)')

# Plot Actual Frequency (Stock Out)
plt.plot(df['Expected_Note'], df['Actual_Frequency_StockOut'], marker='o', linestyle='--', label='Actual Frequency (Stock Out)')

# Graph labels and title
plt.title('Tuning Comparison')
plt.xlabel('Notes')
plt.ylabel('Frequency (Hz)')
plt.grid(True)
plt.legend()

# Show the plot
plt.tight_layout()
plt.show()