from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Lab(db.Model):
    __tablename__ = 'labs'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    heure_creation = db.Column(db.DateTime, default=datetime.utcnow)
    network_name = db.Column(db.String(100), nullable=False)
    subnet = db.Column(db.String(50), nullable=False)
    duree = db.Column(db.Integer, nullable=False)  # Durée en minutes
    containers = db.relationship('Container', backref='lab', lazy=True)

class Container(db.Model):
    __tablename__ = 'containers'
    id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    hostname = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    heure_creation = db.Column(db.DateTime, default=datetime.utcnow)