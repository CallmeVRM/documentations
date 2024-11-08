import time
from datetime import datetime
from app import app
from models import db, Lab, Container  # Importez depuis models.py
import subprocess
from sqlalchemy import func, text

def cleanup_expired_labs():
    while True:
        with app.app_context():
            expired_labs = Lab.query.filter(
                func.now() > Lab.heure_creation + Lab.duree * text("interval '1 minute'")
            ).all()
            for lab in expired_labs:
                try:
                    # Arrêter et supprimer les conteneurs associés
                    containers = Container.query.filter_by(lab_id=lab.id).all()
                    for container in containers:
                        subprocess.run(['docker', 'rm', '-f', container.nom], check=True)
                        db.session.delete(container)
                    # Supprimer le réseau Docker
                    subprocess.run(['docker', 'network', 'rm', lab.network_name], check=True)
                    # Supprimer le lab de la base de données
                    db.session.delete(lab)
                    db.session.commit()
                    print(f"Lab '{lab.nom}' et ses conteneurs ont été supprimés.")
                except Exception as e:
                    db.session.rollback()
                    print(f"Erreur lors de la suppression du lab '{lab.nom}' : {e}")
        # Attendre avant la prochaine vérification
        time.sleep(60)

if __name__ == '__main__':
    cleanup_expired_labs()
