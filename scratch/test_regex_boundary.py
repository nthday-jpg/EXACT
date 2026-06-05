import re

text1 = "William Dickinson was a British politician. Katelyn went to skate with Kate."
orig1 = "William Dickinson"
rep1 = "A"
res1 = re.sub(rf'\b{re.escape(orig1)}\b', rep1, text1)
print(f"Res1: {res1}")

orig2 = "Kate"
rep2 = "B"
res2 = re.sub(rf'\b{re.escape(orig2)}\b', rep2, res1)
print(f"Res2: {res2}")
