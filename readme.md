Journey Through Europe
======================

This repo contains an online version of the board game Journey Through Europe.
Instructions and the rules of the game are written out on the [JTE page on
my website](http://joesingo.co.uk/projects/journey-through-europe/).

Installation
------------

JTE is written in Python as a Flask app.

In development
--------------

To run in development, create and activate a python3 virtual environment and run

```
pip install -r requirements.txt
cd src
python server.py
```

The game will then be accessible at `http://localhost:5000/create/`.


Using Docker
------------

The Docker image starts the Flask app on port 5000, and runs a script to
automatically delete games that have not been updated in over 3 hours.

```
docker build -t jte .
docker run -d -p 5000:5000 jte
```
