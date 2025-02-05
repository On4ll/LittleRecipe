# LittleRecipe  

LittleRecipe calculates food recipe combinations based on given conditions for the game **Elin**.  

While it provides the best possible results for most recipes, the calculations are **approximate** due to the many **variants** of the same food items in the game. Additionally, for recipes with more than 2–3 ingredients, the number of possible combinations becomes too large for normal computers to check exhaustively.  

### Accuracy and Performance  
- Applying too many filtering conditions may exclude some valid recipe combinations, but this is rare.  
- If you have a powerful PC, you can **increase the computation depth** in the settings to search for additional recipes that might otherwise be discarded due to providing only **small stat increases**.   

---

![1](https://github.com/user-attachments/assets/fe324511-e439-4a38-b468-8590eb8eb34b)

## **How to Run**  

### **Using the Executable (No Python Required)**  
You can run the program using **LittleRecipe.exe** without needing to install Python.  
Check the **[latest release here](https://github.com/On4ll/LittleRecipe/releases/tag/Latest))** for the executable file.  

### **Using Python (Source Code)**  
1. Ensure that `Foods.xlsx` and `little_recipe.py` are in the **same folder**.  
2. Run the `little_recipe.py` file.  

---

## **Requirements**  
The following Python libraries are required to run the program:  

- `pandas`  
- `numpy`  
- `tkinter`  
- `tqdm`  
- `customtkinter`

![2](https://github.com/user-attachments/assets/e5a53fa3-30f8-478b-b4d4-73f3cb88935c)
![4](https://github.com/user-attachments/assets/52fb5ca4-6783-4d06-89d8-6e000135fda8)
![5](https://github.com/user-attachments/assets/a143e766-f69d-4fa9-849c-54f0fee006a1)
