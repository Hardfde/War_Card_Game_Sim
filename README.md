# War Game
This is War Card Game Simulator with real-time ML-based win probability calculations. Play a game 
and manually simulate each battle, or autoplay with adjustable speed (1 - 25 battles / second) until 
game ends. Comes with a graph that tracks probability of a win over total turns and the the choice 
between 4 different ML models.

The inspiration behind this project was to learn more about FastAPI, JavaScript, HTML, and CSS, as well as 
learning more about the war card game.

## Frontend
The frontend defines a user interface which gives the options to create a new game, simulate 
one battle (essentially playing one hand), simulate battles at a rate from 1 - 25 battles / second, 
and choose the Machine Learning model the predict the probability of each person winning. There is 
also a graph of the probability over time of player1 winning.

## Backend
The backend contains simulation.py, which has the core war game logic, and simulates battles. Both Features_model.py and 
Features_partial.py calculate the stats used the the machine learning model, which is trained and evaluated in train.py and 
stored in the models folder. Main connects the frontend and the backend.


## Setup
 
### Backend
 
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
 
python3 train.py --games 10000    # generates data and trains all 4 models
uvicorn main:app --reload
```
 
Backend runs at `http://localhost:8000`. Interactive API docs at `http://localhost:8000/docs`.
 
### Frontend
 
```bash
cd frontend
python3 -m http.server 3000
```
 
Open `http://localhost:3000` in a browser. Backend must be running for probability updates to work.

