# LittleRecipe  

LittleRecipe calculates food recipe combinations based on given conditions for the game **Eternal League of Nefia (Elin)**.  

While it provides the best possible results for most recipes, the calculations are **approximate** due to the many **variants** of the same food items in the game. Additionally, for recipes with more than 2–3 ingredients, the number of possible combinations becomes too large for normal computers to check exhaustively.  

### Accuracy and Performance  
- Applying too many filtering conditions may exclude some valid recipe combinations, but this is rare.  
- If you have a powerful PC, you can **increase the computation depth** in the settings to search for additional recipes that might otherwise be discarded due to providing only **small stat increases**.  
- When calculating **potential stat gains** (e.g., Strength Potential, Dexterity Potential), the final potential values may have a **minor deviation** of about **1–2 points** for high-stat foods.  

---

## **How to Run**  

### **Using the Executable (No Python Required)**  
You can run the program using **LittleRecipe.exe** without needing to install Python.  
Check the **[latest release here]([https://github.com/yourusername/LittleRecipe/releases/latest (https://github.com/On4ll/LittleRecipe/releases/tag/Latest))** for the executable file.  

### **Using Python (Source Code)**  
1. Ensure that `Foods.xlsx` and `little_recipe.py` are in the **same folder**.  
2. Run the `little_recipe.py` file.  

---

## **Requirements**  
The following Python libraries are required to run the program:  
