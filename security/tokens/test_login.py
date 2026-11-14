from login import login
from tokens import check_token

# Test 1: each account gets the right role
expected = {"comandant": "astronaut", "specialist2": "astronaut",
            "medic": "medical_officer", "inginer": "astronaut", "earth": "earth"}
passwords = {"comandant": "cm1-shadow", "specialist2": "cm2-shadow",
             "medic": "cm3-shadow", "inginer": "cm4-shadow", "earth": "earth-shadow"}
for user, role in expected.items():
    claims = check_token(login(user, passwords[user]), [role])
    assert claims["role"] == role
print("Test 1 passed: all 5 accounts get the right role")

try:
    login("medic", "wrong")
    print("Test 2 FAILED")
except PermissionError:
    print("Test 2 passed: wrong password rejected")

for i in range(5):
    try:
        login("inginer", "guess" + str(i))
    except PermissionError:
        pass
try:
    login("inginer", "cm4-shadow")
    print("Test 3 FAILED")
except PermissionError as e:
    print("Test 3 passed: account locked ->", e)

try:
    login("hacker", "x")
except PermissionError as e:
    print("Test 4 passed: unknown user ->", e)
