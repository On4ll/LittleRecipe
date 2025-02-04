import pandas as pd
import os
import numpy as np
import tkinter as tk
from tkinter import messagebox, filedialog
from tqdm import tqdm
import customtkinter as ctk  # Modern UI library
from tkinter import IntVar
import json
import sys
import logging
from datetime import datetime  # For timestamping log entries

# Set paths
current_dir = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.join(current_dir, "Foods.xlsx")
output_path = os.path.join(current_dir, "Foods_Calculated.xlsx")

# Set up logging to save console output to a log file
log_file_path = os.path.join(current_dir, "little_recipe.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)
    ]
)

# Load data and preprocess
data = pd.read_excel(input_path)
data['IngreType'] = data['IngreType'].str.split(', ')
data['Tag'] = data['Tag'].str.split(', ')  # Split tags into lists
stat_cols = [col for col in data.columns if col not in ['Foods', 'IngreType', 'Tag']]

# Convert stats to numpy arrays for faster calculations
foods_list = data.to_dict('records')
for food in foods_list:
    food['stats'] = np.array([food[col] for col in stat_cols])

# Get unique tags from the "Tag" column
unique_tags = set()
for tags in data['Tag']:
    if isinstance(tags, list):  # Check if tags are not NaN or empty
        unique_tags.update(tags)
unique_tags = sorted(unique_tags)  # Sort tags alphabetically

# Variable to control tqdm output visibility in the console
SHOW_TQDM_IN_CONSOLE = False  # Set to False to disable tqdm output in the console

# Add this function to check if an ingredient contains the word "cha"
def contains_cha(ingredient_name):
    return "cha" in ingredient_name.lower().split()

# Beam Search
def beam_search(recipe, priority_stats, tag_allowed_foods, banned_ingredients, must_have_ingredients, top_x=5, progress_callback=None, depth=1, calculation_mode=0):
    beam_width = (1000 if len(recipe) > 2 else 100000) * depth
    slots = []
    for ingre_type in recipe:
        valid_foods = [food for food in tag_allowed_foods if ingre_type in food['IngreType'] and not any(ban.lower() in food['Foods'].lower() for ban in banned_ingredients)]
        valid_foods.sort(
            key=lambda x: sum(x[stat] for stat in priority_stats),
            reverse=True
        )
        slots.append(valid_foods)

    beam = [([], np.zeros(len(stat_cols)))]
    total_slots = len(slots)
    
    # Initialize iteration counters
    total_iterations = 0
    start_time = datetime.now()

    for i, slot in enumerate(tqdm(slots, desc="Processing recipe slots", disable=not SHOW_TQDM_IN_CONSOLE)):
        new_beam = []
        for combo_foods, combo_stats in tqdm(beam, desc=f"Slot {i+1}", leave=False, disable=not SHOW_TQDM_IN_CONSOLE):
            for food in slot:
                new_stats = combo_stats + food['stats']
                
                # Deduct 1 for every pair of the same stat
                for stat_index in range(len(stat_cols)):
                    if combo_stats[stat_index] > 0 and food['stats'][stat_index] > 0:
                        new_stats[stat_index] -= 1
                
                new_combo = combo_foods + [food['Foods']]
                new_beam.append((new_combo, new_stats))
                total_iterations += 1  # Increment iteration counter
        
        # Sort the new_beam based on the calculation_mode
        if calculation_mode == 0:
            new_beam.sort(
                key=lambda x: (sum(x[1][stat_cols.index(stat)] for stat in priority_stats), sum(x[1])),
                reverse=True
            )
        elif calculation_mode == 1:
            new_beam.sort(
                key=lambda x: (sum(x[1][stat_cols.index(stat)] * x[1][stat_cols.index(f"{stat}_pot")] if f"{stat}_pot" in priority_stats else x[1][stat_cols.index(stat)] for stat in priority_stats), sum(x[1])),
                reverse=True
            )
        else:
            new_beam.sort(
                key=lambda x: (sum(x[1][stat_cols.index(stat)] for stat in priority_stats), sum(x[1])),
                reverse=True
            )
        beam = new_beam[:beam_width]

        # Update progress bar
        if progress_callback:
            progress = (i + 1) / total_slots
            progress_callback(progress, total_iterations)
    
    # Calculate iterations per second
    end_time = datetime.now()
    time_elapsed = (end_time - start_time).total_seconds()
    iterations_per_second = total_iterations / time_elapsed if time_elapsed > 0 else 0

    # Log the total iterations and iterations per second
    logging.info(f"Total iterations: {total_iterations}")
    logging.info(f"Iterations per second: {iterations_per_second:.2f}")

    results = []
    for combo, stats in beam:
        stat_dict = {stat_cols[i]: int(stats[i]) for i in range(len(stat_cols))}  # Convert stats to integers

        # Ensure "per" stat is not lower than -2
        if "per" in stat_dict and stat_dict["per"] < -2:
            stat_dict["per"] = -2

        if all(stat_dict[stat] > 0 for stat in priority_stats):
            # Ensure the must-have ingredients appear the exact number of times
            if must_have_ingredients:
                combo_ingredients = [ing.lower() for ing in combo]
                must_have_counts = {must: must_have_ingredients.count(must) for must in set(must_have_ingredients)}

                combo_counts = {must: sum(1 for food in combo_ingredients if must.lower() in food.lower()) for must in set(must_have_ingredients)}

                if not all(combo_counts.get(must, 0) >= count for must, count in must_have_counts.items()):
                    continue  # Skip this combination if it doesn't include all must-have ingredients the required number of times

            # Check if more than one ingredient contains the word "cha"
            cha_count = sum(1 for ingredient in combo if contains_cha(ingredient))
            if cha_count > 1:
                continue  # Skip this combination if it contains more than one "cha" ingredient

            results.append({
                'Combination': ', '.join(combo),
                **stat_dict
            })
    
    # Final sorting based on calculation_mode
    if calculation_mode == 0:
        results.sort(
            key=lambda x: (sum(x[stat] for stat in priority_stats), sum(x[stat] for stat in stat_cols if stat not in priority_stats)),
            reverse=True
        )
    elif calculation_mode == 1:
        results.sort(
            key=lambda x: (sum(x[stat] * x[f"{stat}_pot"] if f"{stat}_pot" in priority_stats else x[stat] for stat in priority_stats), sum(x[stat] for stat in stat_cols if stat not in priority_stats)),
            reverse=True
        )
    else:
        results.sort(
            key=lambda x: (sum(x[stat] for stat in priority_stats), sum(x[stat] for stat in stat_cols if stat not in priority_stats)),
            reverse=True
        )

    '''
    # Log the best recipes calculated
    logging.info("Best recipes calculated:")
    for i, result in enumerate(results[:top_x], 1):
        logging.info(f"Recipe {i}: {result['Combination']}")
        for stat, value in result.items():
            if stat != "Combination":
                logging.info(f"  {stat}: {value}")
    
    # Add a separator line for clarity
    logging.info("-----------------------------------------------------------------------------------------\n")
    '''

    return results[:top_x]

# Define colors for ingredient types
INGREDIENT_COLORS = {
    "Meat": "#cc314b",
    "Cheese": "#f5ea22",
    "Vegetable": "#2bf032",
    "Fruit": "#66cc69",
    "Tempura Flour": "#bddbd8",
    "Cake Dough": "#c0f0e1",
    "Gelatine": "#7e918b",
    "Fish": "#68b1e8",
    "Bag of Rice": "#e1eef7",
    "Bread Dough": "#a65656",
    "Dough": "#947b7b",
    "Egg": "#ebdfdf",
    "Flour": "#e7ebdf",
    "Nut": "#d4ed91",
    "Pot of Noodle": "#dbe090",
    "Sauce": "#e82074",
    "Seasoning": "#5de892",
    # Add more ingredient types and colors as needed
}

# Define colors for priority stats
PRIORITY_STAT_COLORS = {
    "str": "#b33b49",
    "end": "#f2541f",
    "dex": "#59de90",
    "per": "#59ded3",
    "ler": "#596fde",
    "wil": "#8359de",
    "mag": "#ba59de",
    "cha": "#f21ff2",
    "str_pot": "#b33b49",
    "end_pot": "#f2541f",
    "dex_pot": "#59de90",
    "per_pot": "#59ded3",
    "ler_pot": "#596fde",
    "wil_pot": "#8359de",
    "mag_pot": "#ba59de",
    "cha_pot": "#f21ff2",
    # Add more stats and colors as needed
}

# Modern Tkinter UI
class RecipeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Little Recipe")  # Updated window title
        self.resizable(False, True)

        # Center the window on the screen
        self.update_idletasks()
        mscreen_width = self.winfo_screenwidth()
        mscreen_height = self.winfo_screenheight()
        mwindow_width = 1085
        mwindow_height = 600

        mx_position = (mscreen_width - mwindow_width) // 2
        my_position = (mscreen_height - mwindow_height) // 2

        self.geometry(f"{mwindow_width}x{mwindow_height}+{mx_position}+{my_position}")

        # Appearance settings
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Recipe ingredients list
        self.recipe = []

        # Priority stats list
        self.priority_stats = []

        # Banned ingredients list
        self.banned_ingredients = []

        # Must-have ingredients list
        self.must_have_ingredients = []

        # Search depth (default is 1)
        self.depth = 1

        self.calculation_mode = IntVar(value=1)  # 0: Maximize Food Stat Level, 1: Maximize XP Gain, 2: Coming Soon!

        # Tags and their checkboxes
        self.tag_checkboxes = {}  # Store checkboxes for tags
        self.selected_tags = set(unique_tags)  # All tags are selected by default

        # Calculation warnings
        self.calculation_warnings = [
            "Depth 1: Fastest but least accurate.(Recommended)\n\nApproximate calculation time multiplier:\n1 Ingredient Recipe: 1x\n2 Ingredient Recipe: 1x\n3 Ingredient Recipe: 1x\n4 Ingredient Recipe: 1x\n5 Ingredient Recipe: 1x",
            "Depth 2: Slightly slower but more accurate.\n\nApproximate calculation time multiplier:\n1 Ingredient Recipe: 10x\n2 Ingredient Recipe: 100x\n3 Ingredient Recipe: 1000x\n4 Ingredient Recipe: 10000x\n5 Ingredient Recipe: 100000x",
            "Depth 3: Balanced speed and accuracy.\n\nApproximate calculation time multiplier:\n1 Ingredient Recipe: 100x\n2 Ingredient Recipe: 10000x\n3 Ingredient Recipe: 1000000x\n4 Ingredient Recipe: 100000000x\n5 Ingredient Recipe: 10000000000x",
            "Depth 4: More accurate but slower.\n\nApproximate calculation time multiplier:\n1 Ingredient Recipe: 1000x\n2 Ingredient Recipe: 1000000x\n3 Ingredient Recipe: 1000000000x\n4 Ingredient Recipe: 1000000000000x\n5 Ingredient Recipe: 1000000000000000x",
            "Depth 5: Even more accurate but slower.\n\nApproximate calculation time multiplier:\n1 Ingredient Recipe: 10000x\n2 Ingredient Recipe: 100000000x\n3 Ingredient Recipe: 1000000000000x\n4 Ingredient Recipe: 10000000000000000x\n5 Ingredient Recipe: 100000000000000000000x",
            "Depth 6: Slower but highly accurate.\n\nApproximate calculation time multiplier:\n1 Ingredient Recipe: 100000x\n2 Ingredient Recipe: 10000000000x\n3 Ingredient Recipe: 100000000000000x\n4 Ingredient Recipe: 1000000000000000000x\n5 Ingredient Recipe: 1000000000000000000000000x",
            "Depth 7: Very slow but very accurate.\n\nApproximate calculation time multiplier:\n1 Ingredient Recipe: 1000000x\n2 Ingredient Recipe: 1000000000000x\n3 Ingredient Recipe: 10000000000000000x\n4 Ingredient Recipe: 100000000000000000000x\n5 Ingredient Recipe: 1000000000000000000000000000x",
            "Depth 8: Extremely slow but extremely accurate.\n\nApproximate calculation time multiplier:\n1 Ingredient Recipe: 10000000x\n2 Ingredient Recipe: 100000000000000x\n3 Ingredient Recipe: 100000000000000000000x\n4 Ingredient Recipe: 1000000000000000000000000x\n5 Ingredient Recipe: 10000000000000000000000000000000x",
            "Depth 9: Very slow but very accurate.\n\nApproximate calculation time multiplier:\n1 Ingredient Recipe: 100000000x\n2 Ingredient Recipe: 10000000000000000x\n3 Ingredient Recipe: 10000000000000000000000x\n4 Ingredient Recipe: 100000000000000000000000000x\n5 Ingredient Recipe: 100000000000000000000000000000000000x",
            "Depth 10: Slowest but most accurate.\n\nApproximate calculation time multiplier:\n1 Ingredient Recipe: 1000000000x\n2 Ingredient Recipe: 100000000000000000x\n3 Ingredient Recipe: 100000000000000000000000x\n4 Ingredient Recipe: 1000000000000000000000000000x\n5 Ingredient Recipe: 1000000000000000000000000000000000000000x"
        ]

        # Get unique ingredient types
        self.ingredient_types = set()
        for types in data['IngreType']:
            self.ingredient_types.update(types)
        self.ingredient_types = sorted(self.ingredient_types)

        # Main container with scrollbar
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(self.main_container)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ctk.CTkScrollbar(self.main_container, orientation=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.inner_frame = ctk.CTkFrame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        # Inputs
        self.input_frame = ctk.CTkFrame(self.inner_frame)
        self.input_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Ingredient Selection
        self.ingredient_frame = ctk.CTkFrame(self.input_frame)
        self.ingredient_frame.pack(fill=tk.X, pady=5)

        self.ingredient_label = ctk.CTkLabel(self.ingredient_frame, text="Add Ingredients to Recipe:", font=("Arial", 20))
        self.ingredient_label.pack(pady=5)

        self.ingredient_button_frame = ctk.CTkFrame(self.ingredient_frame)
        self.ingredient_button_frame.pack(fill=tk.X, pady=5)

        # Dynamically add buttons for each ingredient type
        self.ingredient_rows = []  # Store rows dynamically
        row_frame = ctk.CTkFrame(self.ingredient_button_frame)
        row_frame.pack(fill=tk.X, pady=2)
        self.ingredient_rows.append(row_frame)

        self.ingredient_buttons = {}
        buttons_per_row = 7  # Limit per row
        count = 0

        for ingre_type in self.ingredient_types:
            if count >= buttons_per_row:
                row_frame = ctk.CTkFrame(self.ingredient_button_frame)
                row_frame.pack(fill=tk.X, pady=2)
                self.ingredient_rows.append(row_frame)
                count = 0

            color = INGREDIENT_COLORS.get(ingre_type, "#FFFFFF")  # Assign color
            button = ctk.CTkButton(
                row_frame,
                text=ingre_type,
                fg_color=color,
                text_color="black" if color != "#FFFFFF" else "white",
                command=lambda t=ingre_type: self.add_ingredient(t)
            )
            button.pack(side=tk.LEFT, padx=5, pady=5)

            self.ingredient_buttons[ingre_type] = button
            count += 1  # Increment count for row tracking

        # Recipe Display
        self.recipe_display_frame = ctk.CTkFrame(self.input_frame)
        self.recipe_display_frame.pack(fill=tk.X, pady=5)

        self.recipe_label = ctk.CTkLabel(self.recipe_display_frame, text="Current Recipe:", font=("Arial", 20))
        self.recipe_label.pack(pady=5)

        self.recipe_buttons_frame = ctk.CTkFrame(self.recipe_display_frame, width=800, height=100, fg_color="#3e4e59")
        self.recipe_buttons_frame.pack_propagate(False)
        self.recipe_buttons_frame.pack(fill=tk.X, pady=5)

        # Tag Checkbox Bar
        self.tag_frame = ctk.CTkFrame(self.recipe_display_frame)
        self.tag_frame.pack(fill=tk.X, pady=5)

        self.tag_label = ctk.CTkLabel(self.tag_frame, text="Allowed Tags:", font=("Arial", 20))
        self.tag_label.pack(pady=5)

        # Dynamically add checkboxes for each tag
        self.tag_checkbox_frame = ctk.CTkFrame(self.tag_frame)
        self.tag_checkbox_frame.pack(fill=tk.X, pady=5)

        for tag in unique_tags:
            checkbox = ctk.CTkCheckBox(
                self.tag_checkbox_frame,
                text=tag,
                command=lambda t=tag: self.update_selected_tags(t)
            )
            checkbox.pack(side=tk.LEFT, padx=5, pady=5)
            checkbox.select()  # Select by default
            self.tag_checkboxes[tag] = checkbox

        # Priority Stats
        self.priority_frame = ctk.CTkFrame(self.input_frame)
        self.priority_frame.pack(fill=tk.X, pady=5)

        self.priority_button_frame = ctk.CTkFrame(self.priority_frame)
        self.priority_button_frame.pack(fill=tk.X, pady=5)

        # Dynamically add Priority Stats buttons
        self.priority_rows = []  # Store rows dynamically
        row_frame = ctk.CTkFrame(self.priority_button_frame)
        row_frame.pack(fill=tk.X, pady=2)
        self.priority_rows.append(row_frame)

        self.priority_buttons = {}
        buttons_per_row = 7  # Limit per row
        count = 0

        for stat in stat_cols:
            if count >= buttons_per_row:
                row_frame = ctk.CTkFrame(self.priority_button_frame)
                row_frame.pack(fill=tk.X, pady=2)
                self.priority_rows.append(row_frame)
                count = 0

            color = PRIORITY_STAT_COLORS.get(stat, "#ADD8E6")  # Assign color for stats
            button = ctk.CTkButton(
                row_frame,
                text=stat,
                fg_color=color,
                text_color="black" if color != "#FFFFFF" else "white",
                command=lambda s=stat: self.add_priority_stat(s)
            )
            button.pack(side=tk.LEFT, padx=5, pady=5)

            self.priority_buttons[stat] = button
            count += 1  # Increment count for row tracking
           
        # Priority Label
        self.priority_label = ctk.CTkLabel(self.priority_button_frame, text="Prioritized Stats:", font=("Arial", 20))
        self.priority_label.pack(pady=5)
        
        # Priority Display
        self.priority_display_frame = ctk.CTkFrame(self.input_frame, width=800, height=100, fg_color="#3e4e59")
        self.priority_display_frame.pack_propagate(False)
        self.priority_display_frame.pack(fill=tk.X, pady=5)

        # Number of Top Recipes Input
        self.top_x_frame = ctk.CTkFrame(self.input_frame)
        self.top_x_frame.pack(fill=tk.X, pady=5)

        self.top_x_label = ctk.CTkLabel(self.top_x_frame, text="Number of Top Recipes to Show:", font=("Arial", 20))
        self.top_x_label.pack(side=tk.LEFT, padx=5)

        self.top_x_entry = ctk.CTkEntry(self.top_x_frame, width=50, font=("Arial", 20))
        self.top_x_entry.insert(0, "5")  # Default value
        self.top_x_entry.pack(side=tk.LEFT, padx=5)

        # Calculate Button
        self.calculate_button = ctk.CTkButton(self.input_frame, text="Calculate Best Recipes",width=200, height=50, font=("Arial", 20), fg_color="#ffffff", text_color="#3f7ef2", command=self.calculate_recipes)
        self.calculate_button.pack(pady=10)

        # Progress Bar and Label
        self.progress_frame = ctk.CTkFrame(self.input_frame)
        self.progress_frame.pack(fill=tk.X, pady=10)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=300)
        self.progress_bar.pack(side=tk.TOP, padx=5)
        self.progress_bar.set(0)  # Initialize progress bar to 0

        # Label to display "checked/maximum to check"
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="0 / 0", font=("Arial", 16))
        self.progress_label.pack(side=tk.TOP, padx=5)

        # Save and Load Preset Buttons
        self.preset_buttons_frame = ctk.CTkFrame(self.input_frame)
        self.preset_buttons_frame.pack(fill=tk.X, pady=5)

        self.save_preset_button = ctk.CTkButton(self.preset_buttons_frame, text="Save Preset", width=150, command=self.save_preset)
        self.save_preset_button.pack(side=tk.LEFT, padx=5)

        self.load_preset_button = ctk.CTkButton(self.preset_buttons_frame, text="Load Preset", width=150, command=self.load_preset)
        self.load_preset_button.pack(side=tk.LEFT, padx=5)

        # Settings Button
        self.settings_button = ctk.CTkButton(self.preset_buttons_frame, text="Settings", width=150, command=self.open_settings)
        self.settings_button.pack(side=tk.RIGHT, padx=5)

        # Save and Load Banned Ingredients Buttons
        self.ban_buttons_frame = ctk.CTkFrame(self.input_frame)
        self.ban_buttons_frame.pack(fill=tk.X, pady=5)

        self.save_ban_button = ctk.CTkButton(self.ban_buttons_frame, text="Save Banned List", width=150, command=self.save_banned_list)
        self.save_ban_button.pack(side=tk.LEFT, padx=5)

        self.load_ban_button = ctk.CTkButton(self.ban_buttons_frame, text="Load Banned List", width=150, command=self.load_banned_list)
        self.load_ban_button.pack(side=tk.LEFT, padx=5)

        # Credits Button
        self.credits_button = ctk.CTkButton(self.ban_buttons_frame, text="Credits", width=150, command=self.show_credits)
        self.credits_button.pack(side=tk.RIGHT, padx=5)

        # Ban Ingredient Section
        self.ban_frame = ctk.CTkFrame(self.input_frame)
        self.ban_frame.pack(fill=tk.X, pady=5)

        self.ban_label = ctk.CTkLabel(self.ban_frame, text="Banned Ingredients (comma-separated):", font=("Arial", 20))
        self.ban_label.pack(pady=5)

        self.ban_entry = ctk.CTkEntry(self.ban_frame, width=300)
        self.ban_entry.pack(pady=5)
        self.ban_entry.bind("<Return>", lambda e: self.update_banlist_from_entry())

        # Banlist Display
        self.banlist_display_frame = ctk.CTkFrame(self.input_frame, width=800, height=130, fg_color="#3e4e59")
        self.banlist_display_frame.pack_propagate(False)
        self.banlist_display_frame.pack(fill=tk.X, pady=5)

        # Scrollable frame for banned ingredients
        self.banlist_scroll_frame = ctk.CTkScrollableFrame(self.banlist_display_frame, width=800, height=130, fg_color="#3e4e59")
        self.banlist_scroll_frame.pack(fill=tk.BOTH, expand=True)

        # Must-Have Ingredient Section
        self.must_have_frame = ctk.CTkFrame(self.input_frame)
        self.must_have_frame.pack(fill=tk.X, pady=5)

        self.must_have_label = ctk.CTkLabel(self.must_have_frame, text="Must-Have Ingredients (comma-separated):", font=("Arial", 20))
        self.must_have_label.pack(pady=5)

        self.must_have_entry = ctk.CTkEntry(self.must_have_frame, width=300)
        self.must_have_entry.pack(pady=5)
        self.must_have_entry.bind("<Return>", lambda e: self.update_must_have_from_entry())

        # Must-Have Display
        self.must_have_display_frame = ctk.CTkFrame(self.input_frame, width=800, height=100, fg_color="#3e4e59")
        self.must_have_display_frame.pack_propagate(False)
        self.must_have_display_frame.pack(fill=tk.X, pady=5)

        # Bind mouse wheel to scroll for all widgets in the inner frame
        self._bind_mousewheel_scroll(self.inner_frame)

    def update_selected_tags(self, tag):
        """Update the selected tags based on checkbox state."""
        if self.tag_checkboxes[tag].get() == 1:
            self.selected_tags.add(tag)
        else:
            self.selected_tags.discard(tag)

        #print(self.selected_tags)

    def show_credits(self):
        """Open a new window to display credits."""
        credits_window = ctk.CTkToplevel(self)
        credits_window.title("Credits")
        credits_window.geometry("300x100")

        # Center the window on the screen
        credits_window.update_idletasks()
        screen_width = credits_window.winfo_screenwidth()
        screen_height = credits_window.winfo_screenheight()
        window_width = 300
        window_height = 100

        x_position = (screen_width // 2) - (window_width // 2)
        y_position = (screen_height // 2) - (window_height // 2)

        credits_window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        self.after(100, lambda: credits_window.focus_force()) # Bring the window to the front

        # Add credits text
        credits_label = ctk.CTkLabel(credits_window, text="@On4ll\n@mRain", font=("Arial", 20))
        credits_label.pack(pady=20)

    def _bind_mousewheel_scroll(self, widget):
        """Recursively bind mouse wheel to all widgets for scrolling."""
        widget.bind("<MouseWheel>", self._on_mousewheel)
        for child in widget.winfo_children():
            self._bind_mousewheel_scroll(child)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def add_ingredient(self, ingredient):
        if len(self.recipe) >= 5:
            messagebox.showwarning("Warning", "Maximum 5 ingredients can be added to the recipe.")
            return
        self.recipe.append(ingredient)
        self.update_recipe_display()

    def update_recipe_display(self):
        # Clear the recipe buttons frame
        for widget in self.recipe_buttons_frame.winfo_children():
            widget.destroy()

        # Create new row containers dynamically
        row_frame = ctk.CTkFrame(self.recipe_buttons_frame)
        row_frame.pack(fill=tk.X, pady=2)
        count = 0

        for i, item in enumerate(self.recipe):
            if count >= 7:
                row_frame = ctk.CTkFrame(self.recipe_buttons_frame)
                row_frame.pack(fill=tk.X, pady=2)
                count = 0

            color = INGREDIENT_COLORS.get(item, "#FFFFFF")  # Use assigned color

            frame = ctk.CTkFrame(row_frame, corner_radius=10, fg_color=color)
            frame.pack(side=tk.LEFT, padx=5, pady=5)

            label = ctk.CTkLabel(frame, text=item, text_color="black")
            label.pack(side=tk.LEFT, padx=5)

            cross_button = ctk.CTkButton(
                frame,
                text="×",
                width=20,
                height=20,
                fg_color="transparent",
                text_color="black",
                hover_color="#FF0000",
                command=lambda i=item: self.remove_ingredient(i)
            )
            cross_button.pack(side=tk.RIGHT, padx=5)

            count += 1  # Track number of items in row

        # Bind mouse wheel to scroll
        row_frame.bind("<MouseWheel>", self._on_mousewheel)

    def remove_ingredient(self, ingredient):
        if ingredient in self.recipe:
            self.recipe.remove(ingredient)
            self.update_recipe_display()

    def add_priority_stat(self, stat):
        if stat not in self.priority_stats:
            self.priority_stats.append(stat)
            self.update_priority_display()

    def update_priority_display(self):
        # Clear the priority display frame
        for widget in self.priority_display_frame.winfo_children():
            widget.destroy()

        # Add each priority stat as a rounded button with a cross
        row_frame = ctk.CTkFrame(self.priority_display_frame)
        row_frame.pack(fill=tk.X, pady=2)
        count = 0

        for i, stat in enumerate(self.priority_stats):
            if count >= 7:
                row_frame = ctk.CTkFrame(self.priority_display_frame)
                row_frame.pack(fill=tk.X, pady=2)
                count = 0

            color = PRIORITY_STAT_COLORS.get(stat, "#ADD8E6")  # Use assigned color
            frame = ctk.CTkFrame(row_frame, corner_radius=10, fg_color=color)
            frame.pack(side=tk.LEFT, padx=5, pady=5)

            label = ctk.CTkLabel(frame, text=stat, text_color="black")
            label.pack(side=tk.LEFT, padx=5)

            cross_button = ctk.CTkButton(
                frame,
                text="×",
                width=20,
                height=20,
                fg_color="transparent",
                text_color="black",
                hover_color="#FF0000",
                command=lambda s=stat: self.remove_priority_stat(s)
            )
            cross_button.pack(side=tk.RIGHT, padx=5)

            count += 1  # Track number of items in row

        # Bind mouse wheel to scroll
        row_frame.bind("<MouseWheel>", self._on_mousewheel)

    def remove_priority_stat(self, stat):
        if stat in self.priority_stats:
            self.priority_stats.remove(stat)
            self.update_priority_display()

    # Modify the calculate_recipes method to pass the calculation mode to beam_search
    def calculate_recipes(self):
        if not self.recipe:
            messagebox.showwarning("Warning", "Please add at least one ingredient to the recipe.")
            return

        if not self.priority_stats:
            messagebox.showwarning("Warning", "Please add at least one priority stat.")
            return

        try:
            top_x = int(self.top_x_entry.get())
        except ValueError:
            messagebox.showwarning("Warning", "Please enter a valid number for top recipes.")
            return

        # Get banned ingredients
        banned_ingredients = [ingredient.strip().lower() for ingredient in self.ban_entry.get().split(",") if ingredient.strip()]
        banned_ingredients = list(set(banned_ingredients))
        self.banned_ingredients = banned_ingredients

        # Get must-have ingredients
        must_have_ingredients = [ingredient.strip().lower() for ingredient in self.must_have_entry.get().split(",") if ingredient.strip()]
        self.must_have_ingredients = must_have_ingredients

        # Filter ingredients based on selected tags
        tag_allowed_foods = []
        for food in foods_list:
            if not isinstance(food['Tag'], list):  # Add if tags are missing because it's a normal ingredient
                tag_allowed_foods.append(food)
                continue
            # Check if the food has any of the deselected tags
            if any(tag not in self.selected_tags for tag in food['Tag']):
                continue  # Skip this food if it has any deselected tag
            tag_allowed_foods.append(food)

        # Reset progress bar and label
        self.progress_bar.set(0)
        self.progress_label.configure(text="0 / 0")
        self.update()

        # Calculate the total number of combinations to check
        total_combinations = 1
        for ingre_type in self.recipe:
            valid_foods_for_type = [food for food in tag_allowed_foods if ingre_type in food['IngreType'] and not any(ban.lower() in food['Foods'].lower() for ban in banned_ingredients)]
            total_combinations *= len(valid_foods_for_type)

        # Adjust total combinations based on depth
        total_combinations *= (10 ** (self.depth - 1)) ** len(self.recipe)

        # Perform beam search with progress updates
        def update_progress(progress, checked_combinations):
            self.progress_bar.set(progress)
            self.progress_label.configure(text=f"{checked_combinations} / {total_combinations}")
            self.update()

        best_combinations = beam_search(
            self.recipe,
            self.priority_stats,
            tag_allowed_foods, 
            banned_ingredients,
            must_have_ingredients,
            top_x=top_x,
            progress_callback=lambda progress, checked: update_progress(progress, checked),
            depth=self.depth,
            calculation_mode=self.calculation_mode.get()
        )

        # Update progress bar to 100%
        self.progress_bar.set(1)
        self.progress_label.configure(text=f"{total_combinations} / {total_combinations}")
        self.update()

        # Open new window to show results
        result_window = ctk.CTkToplevel(self)
        result_window.title("Best Recipes Results")
        result_window.geometry("800x600")

        # Center the window on the screen
        result_window.update_idletasks()
        screen_width = result_window.winfo_screenwidth()
        screen_height = result_window.winfo_screenheight()
        window_width = 950
        window_height = 600

        x_position = (screen_width // 2) - (window_width // 2)
        y_position = (screen_height // 2) - (window_height // 2)

        result_window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        self.after(100, lambda: result_window.focus_force())

        # Create a scrollable frame for results
        result_scroll_frame = ctk.CTkScrollableFrame(result_window)
        result_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        if best_combinations:
            for i, combo in enumerate(best_combinations, 1):
                # Recipe combination
                combo_frame = ctk.CTkFrame(result_scroll_frame, corner_radius=10)
                combo_frame.pack(fill=tk.X, pady=5, padx=5)

                # Display ingredients as small rounded buttons
                ingredients_frame = ctk.CTkFrame(combo_frame)
                ingredients_frame.pack(fill=tk.X, pady=5)

                row_frame = ctk.CTkFrame(ingredients_frame)
                row_frame.pack(fill=tk.X, pady=2)
                count = 0

                for ingredient in combo['Combination'].split(', '):
                    if count >= 4:
                        row_frame = ctk.CTkFrame(ingredients_frame)
                        row_frame.pack(fill=tk.X, pady=2)
                        count = 0

                    ingredient_frame = ctk.CTkFrame(row_frame, corner_radius=10, fg_color="#FFFDD0")
                    ingredient_frame.pack(side=tk.LEFT, padx=5, pady=5)

                    include_button = ctk.CTkButton(
                        ingredient_frame,
                        text="Include",
                        width=20,
                        height=20,
                        fg_color="#90EE90",
                        text_color="black",
                        hover_color="#32CD32",
                        command=lambda ing=ingredient: self.add_must_have_ingredient(ing)
                    )
                    include_button.pack(side=tk.LEFT, padx=5)

                    ingredient_label = ctk.CTkLabel(ingredient_frame, text=ingredient, text_color="black")
                    ingredient_label.pack(side=tk.LEFT, padx=5)

                    ban_button = ctk.CTkButton(
                        ingredient_frame,
                        text="Ban",
                        width=20,
                        height=20,
                        fg_color="#f2aab4",
                        text_color="black",
                        hover_color="#FF0000",
                        command=lambda ing=ingredient: self.ban_ingredient(ing)
                    )
                    ban_button.pack(side=tk.RIGHT, padx=5)

                    count += 1  # Track number of items in row

                # Calculate total prioritized stat XP, non-prioritized stat XP, and total XP
                if self.calculation_mode.get() < 2:
                    prioritized_xp = 0
                    non_prioritized_xp = 0
                    #other_stats_xp = 0

                    for stat in combo:
                        if stat == "Combination":
                            continue
                        elif "_pot" in stat:
                            continue
                        elif stat in self.priority_stats:
                            #print("stat: ", stat)
                            #print("f[stat_pot]:", f"{stat}_pot")
                            #print("prioritized stats: ", self.priority_stats)
                            #print("combo = ", combo)
                            #print("combo[stat] = ", combo[stat])
                            #print("combo.get(stat_pot)", combo.get(f"{stat}_pot", 1))
                            prioritized_xp += combo[stat] * combo.get(f"{stat}_pot", 1)
                        else:
                            #print("__before__non_prioritized_xp: ", non_prioritized_xp)
                            temp_pot = combo.get(f"{stat}_pot", 1)
                            non_prioritized_xp += combo[stat] * (1 if temp_pot == 0 else temp_pot)
                            #print("__after__non_prioritized_xp: ", non_prioritized_xp)

                    total_xp = prioritized_xp + non_prioritized_xp

                    # Display XP information
                    xp_text = f"Prioritized XP: {prioritized_xp}\nNon-Prioritized XP: {non_prioritized_xp}\ntotal_xp XP: {total_xp}"
                    xp_label = ctk.CTkLabel(
                        combo_frame, 
                        text=xp_text, 
                        font=("Arial", 12), 
                        anchor="w", 
                        justify="left"
                    )
                    xp_label.pack(fill=tk.X, padx=10, pady=5, anchor="w")

                # Display non-zero stats in text format (left-aligned)
                stats_text = ""
                for stat in sorted(combo.keys(), key=lambda x: combo[x] if x != "Combination" else 0, reverse=True):
                    if stat != "Combination" and combo[stat] != 0:  # Only show non-zero stats
                        stats_text += f"{stat}: {int(combo[stat])}"
                        # If the stat has a corresponding "_pot" stat, calculate and display the product
                        if f"{stat}_pot" in combo and combo[f"{stat}_pot"] != 0:
                            stats_text += f" ({stat} * {stat}_pot = {int(combo[stat] * combo[f'{stat}_pot'])})"
                        stats_text += "\n"

                stats_label = ctk.CTkLabel(
                    combo_frame, 
                    text=stats_text.strip(), 
                    font=("Arial", 12), 
                    anchor="w", 
                    justify="left"
                )
                stats_label.pack(fill=tk.X, padx=10, pady=5, anchor="w")
        else:
            no_results_label = ctk.CTkLabel(result_scroll_frame, text="No valid recipes found.", font=("Arial", 20))
            no_results_label.pack(pady=10)

    def ban_ingredient(self, ingredient):
        current_banned = self.ban_entry.get()
        if current_banned:
            new_banned = f"{current_banned}, {ingredient}"
        else:
            new_banned = ingredient
        self.ban_entry.delete(0, tk.END)
        self.ban_entry.insert(0, new_banned)
        self.banned_ingredients = list(set([ing.lower() for ing in self.banned_ingredients + [ingredient.lower()]]))  # Prevent duplicates
        self.update_banlist_display()

    def add_must_have_ingredient(self, ingredient):
        current_must_have = self.must_have_entry.get()
        if current_must_have:
            new_must_have = f"{current_must_have}, {ingredient}"
        else:
            new_must_have = ingredient
        self.must_have_entry.delete(0, tk.END)
        self.must_have_entry.insert(0, new_must_have)
        self.must_have_ingredients.append(ingredient.lower())
        self.update_must_have_display()

    def update_banlist_from_entry(self):
        banned_ingredients = [ingredient.strip().lower() for ingredient in self.ban_entry.get().split(",") if ingredient.strip()]
        banned_ingredients = list(set(banned_ingredients))  # Remove duplicates
        self.banned_ingredients = banned_ingredients
        self.update_banlist_display()

    def update_must_have_from_entry(self):
        must_have_ingredients = [ingredient.strip().lower() for ingredient in self.must_have_entry.get().split(",") if ingredient.strip()]
        self.must_have_ingredients = must_have_ingredients
        self.update_must_have_display()

    def update_banlist_display(self):
        # Clear the banlist display frame
        for widget in self.banlist_scroll_frame.winfo_children():
            widget.destroy()

        # Add each banned ingredient as a rounded button with a cross
        row_frame = ctk.CTkFrame(self.banlist_scroll_frame)
        row_frame.pack(fill=tk.X, pady=2)
        count = 0

        for i, ingredient in enumerate(self.banned_ingredients):
            if count >= 7:
                row_frame = ctk.CTkFrame(self.banlist_scroll_frame)
                row_frame.pack(fill=tk.X, pady=2)
                count = 0

            frame = ctk.CTkFrame(row_frame, corner_radius=10, fg_color="#FFCCCB")
            frame.pack(side=tk.LEFT, padx=5, pady=5)

            label = ctk.CTkLabel(frame, text=ingredient, text_color="black")
            label.pack(side=tk.LEFT, padx=5)

            cross_button = ctk.CTkButton(
                frame,
                text="×",
                width=20,
                height=20,
                fg_color="transparent",
                text_color="black",
                hover_color="#FF0000",
                command=lambda ing=ingredient: self.remove_banned_ingredient(ing)
            )
            cross_button.pack(side=tk.RIGHT, padx=5)

            count += 1  # Track number of items in row

    def remove_banned_ingredient(self, ingredient):
        if ingredient.lower() in self.banned_ingredients:
            self.banned_ingredients.remove(ingredient.lower())
            self.ban_entry.delete(0, tk.END)
            self.ban_entry.insert(0, ", ".join(self.banned_ingredients))
            self.update_banlist_display()

    def update_must_have_display(self):
        # Clear the must-have display frame
        for widget in self.must_have_display_frame.winfo_children():
            widget.destroy()

        # Add each must-have ingredient as a rounded button with a cross
        row_frame = ctk.CTkFrame(self.must_have_display_frame)
        row_frame.pack(fill=tk.X, pady=2)
        count = 0

        for i, ingredient in enumerate(self.must_have_ingredients):
            if count >= 7:
                row_frame = ctk.CTkFrame(self.must_have_display_frame)
                row_frame.pack(fill=tk.X, pady=2)
                count = 0

            frame = ctk.CTkFrame(row_frame, corner_radius=10, fg_color="#90EE90")
            frame.pack(side=tk.LEFT, padx=5, pady=5)

            label = ctk.CTkLabel(frame, text=ingredient, text_color="black")
            label.pack(side=tk.LEFT, padx=5)

            cross_button = ctk.CTkButton(
                frame,
                text="×",
                width=20,
                height=20,
                fg_color="transparent",
                text_color="black",
                hover_color="#FF0000",
                command=lambda ing=ingredient: self.remove_must_have_ingredient(ing)
            )
            cross_button.pack(side=tk.RIGHT, padx=5)

            count += 1  # Track number of items in row

        # Bind mouse wheel to scroll
        row_frame.bind("<MouseWheel>", self._on_mousewheel)

    def remove_must_have_ingredient(self, ingredient):
        if ingredient.lower() in self.must_have_ingredients:
            self.must_have_ingredients.remove(ingredient.lower())
            self.must_have_entry.delete(0, tk.END)
            self.must_have_entry.insert(0, ", ".join(self.must_have_ingredients))
            self.update_must_have_display()

    def save_banned_list(self):
        """Save the banned ingredient list to a file."""
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if file_path:
            with open(file_path, "w") as file:
                file.write(", ".join(self.banned_ingredients))
            messagebox.showinfo("Success", "Banned ingredient list saved successfully!")

    def load_banned_list(self):
        """Load the banned ingredient list from a file."""
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            with open(file_path, "r") as file:
                banned_ingredients = file.read().strip().split(", ")
                self.banned_ingredients = list(set([ing.lower() for ing in banned_ingredients if ing.strip()]))
                self.ban_entry.delete(0, tk.END)
                self.ban_entry.insert(0, ", ".join(self.banned_ingredients))
                self.update_banlist_display()
            messagebox.showinfo("Success", "Banned ingredient list loaded successfully!")

    def save_preset(self):
        """Save the current preset (recipe, priority stats, banned ingredients, must-have ingredients, and top_x) to a file."""
        preset = {
            "recipe": self.recipe,
            "priority_stats": self.priority_stats,
            "banned_ingredients": self.banned_ingredients,
            "must_have_ingredients": self.must_have_ingredients,
            "top_x": self.top_x_entry.get()
        }
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
        if file_path:
            with open(file_path, "w") as file:
                json.dump(preset, file)
            messagebox.showinfo("Success", "Preset saved successfully!")

    def load_preset(self):
        """Load a preset from a file and update the UI."""
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if file_path:
            with open(file_path, "r") as file:
                preset = json.load(file)
                self.recipe = preset.get("recipe", [])
                self.priority_stats = preset.get("priority_stats", [])
                self.banned_ingredients = preset.get("banned_ingredients", [])
                self.must_have_ingredients = preset.get("must_have_ingredients", [])
                self.top_x_entry.delete(0, tk.END)
                self.top_x_entry.insert(0, preset.get("top_x", "5"))

                # Update the ban entry
                self.ban_entry.delete(0, tk.END)
                self.ban_entry.insert(0, ", ".join(self.banned_ingredients))

                # Update the must-have entry
                self.must_have_entry.delete(0, tk.END)
                self.must_have_entry.insert(0, ", ".join(self.must_have_ingredients))

                # Update UI
                self.update_recipe_display()
                self.update_priority_display()
                self.update_banlist_display()
                self.update_must_have_display()
            messagebox.showinfo("Success", "Preset loaded successfully!")

    def open_settings(self):
        """Open the settings window."""
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("Settings")
        settings_window.geometry("400x400")

        # Center the window on the screen
        settings_window.update_idletasks()  # Ensure the window dimensions are updated
        screen_width = settings_window.winfo_screenwidth()
        screen_height = settings_window.winfo_screenheight()
        window_width = 400
        window_height = 400

        x_position = (screen_width // 2) - (window_width // 2)
        y_position = (screen_height // 2) - (window_height // 2)

        settings_window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        self.after(100, lambda: settings_window.focus_force()) # Bring the window to the front

        # Search Depth Label
        depth_label = ctk.CTkLabel(settings_window, text="Search Depth:", font=("Arial", 16))
        depth_label.pack(pady=10)

        # Slider for search depth
        self.depth_slider = ctk.CTkSlider(settings_window, from_=1, to=10, number_of_steps=9, command=self.update_depth)
        self.depth_slider.set(self.depth)
        self.depth_slider.pack(pady=10)

        # Warning message box
        self.warning_message = ctk.CTkLabel(settings_window, text=self.calculation_warnings[int(self.depth) - 1], font=("Arial", 12), wraplength=350)
        self.warning_message.pack(pady=10)

        # Calculation Mode Label
        mode_label = ctk.CTkLabel(settings_window, text="Calculation Mode:", font=("Arial", 16))
        mode_label.pack(pady=10)

        # Slider for calculation mode
        self.mode_slider = ctk.CTkSlider(settings_window, from_=0, to=2, number_of_steps=2, command=self.update_mode)
        self.mode_slider.set(self.calculation_mode.get())
        self.mode_slider.pack(pady=10)

        # Mode description label
        self.mode_description = ctk.CTkLabel(settings_window, text=self.get_mode_description(self.calculation_mode.get()), font=("Arial", 12), wraplength=350)
        self.mode_description.pack(pady=10)

    def update_mode(self, value):
        """Update the calculation mode based on the slider value."""
        self.calculation_mode.set(int(float(value)))
        self.mode_description.configure(text=self.get_mode_description(self.calculation_mode.get()))

    def get_mode_description(self, mode):
        """Get the description for the selected calculation mode."""
        if mode == 0:
            return "Maximize Food Stat Level: The program will work as it is."
        elif mode == 1:
            return "Maximize XP Gain: The program will try to find the highest value with the condition (stat * stat_pot) for priority stats."
        elif mode == 2:
            return "Coming Soon!"
        return ""

    def update_depth(self, value):
        """Update the search depth based on the slider value."""
        self.depth = int(float(value))
        self.warning_message.configure(text=self.calculation_warnings[self.depth - 1])

# Run the application
if __name__ == "__main__":
    app = RecipeApp()
    app.mainloop()