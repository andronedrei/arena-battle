Cum sa rulezi:

# Setup (doar odata)
cd arena_battle # (sau ce cale ai tu la proiect)

python -m venv venv

source venv/bin/activate # (activare venv pe linux)

pip install -r requirements.txt

# rulare
cd src

# Din 3 terminale diferite rulezi cate una din comenzile
python -m server.main # (rulezi din primul terminal)

python -m client.main

pythin -m client.main

# ATENTIE !!! NU MERGE DIN WSL, DACA AI WINDOWS RULEAZA DIRECT IN WINDOWS DAR ADAPTEAZA COMENZILE
