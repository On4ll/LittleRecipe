import pandas as pd
import os
import numpy as np
from tqdm import tqdm  # For progress tracking

# Set paths
current_dir = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.join(current_dir, "Foods.xlsx")
output_path = os.path.join(current_dir, "Foods_Calculated.xlsx")

# Load data and preprocess
data = pd.read_excel(input_path)
data['IngreType'] = data['IngreType'].str.split(', ')
stat_cols = [col for col in data.columns if col not in ['Foods', 'IngreType']]
priority_stats = ['dex', 'dex_pot']  # Update as needed

# Beam width: Adjust based on performance (e.g., 1000-5000)
BEAM_WIDTH = 1000
TOP_X = 15

# Convert stats to numpy arrays for faster calculations
foods_list = data.to_dict('records')
for food in foods_list:
    food['stats'] = np.array([food[col] for col in stat_cols])

def beam_search(recipe, beam_width=1000):
    # Precompute valid foods for each recipe slot
    slots = []
    for ingre_type in recipe:
        valid_foods = [food for food in foods_list if ingre_type in food['IngreType']]
        valid_foods.sort(
            key=lambda x: sum(x[stat] for stat in priority_stats),
            reverse=True
        )
        slots.append(valid_foods)

    # Initialize beam: list of (current_foods, sum_stats)
    beam = [([], np.zeros(len(stat_cols)))]
    
    # Progress tracking for each slot
    for i, slot in enumerate(tqdm(slots, desc="Processing recipe slots")):
        new_beam = []
        for combo_foods, combo_stats in tqdm(beam, desc=f"Slot {i+1}", leave=False):
            for food in slot:
                # Allow the same ingredient to be used in multiple slots
                new_stats = combo_stats + food['stats']
                new_combo = combo_foods + [food['Foods']]
                new_beam.append((new_combo, new_stats))
        
        # Prune to top beam_width combinations based on priority stats
        new_beam.sort(
            key=lambda x: sum(x[1][stat_cols.index(stat)] for stat in priority_stats),
            reverse=True
        )
        beam = new_beam[:beam_width]
    
    # Convert results to readable format
    results = []
    for combo, stats in beam:
        stat_dict = {stat_cols[i]: stats[i] for i in range(len(stat_cols))}
        if all(stat_dict[stat] > 0 for stat in priority_stats):
            results.append({
                'Combination': ', '.join(combo),
                **stat_dict
            })
    
    # Return top X results
    results.sort(
        key=lambda x: sum(x[stat] for stat in priority_stats),
        reverse=True
    )
    return results[:TOP_X]

# Example usage
recipe = ['vegetable', 'meat', 'cheese', 'dough', 'seasoning']  # Update as needed
best_combinations = beam_search(recipe, BEAM_WIDTH)

# Save results
best_df = pd.DataFrame(best_combinations)
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    best_df.to_excel(writer, sheet_name='Best_Combination', index=False)

print(f"Results saved to {output_path}")