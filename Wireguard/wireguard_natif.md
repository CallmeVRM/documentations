## Installation de WireGuard en IPv4 en mode natif sur debian12 : 

### Configuration du serveur :

#### Etape 1 - Installation
Pour une installation stable, vous pouvez passer par les sources officielles de Debian en exécutant la commande suivante :

```bash
sudo apt update
sudo apt install wireguard -y
```

#### Etape 2 - Configuration

Ensuite, vous allez générer une paire de clés nécessaires à l’authentification et au chiffrement des paquets.

- Pour ouvrir un shell interactif avec des privilèges root :
```bash
sudo -s 
```

- Accédez au répertoire /etc/wireguard :
```bash
cd /etc/wireguard
```

- Définissez les permissions des fichiers qui seront créés dans le dossier /etc/wireguard de manière à ce que seul le propriétaire (root dans ce cas) puisse lire et écrire les fichiers. Ensuite, créez une paire de clés privée/publique sous le nom "privatekey" et "publickey" :

```bash
umask 277 && wg genkey | tee privatekey | wg pubkey > publickey
```

- Optionnellement, vous pouvez ajouter une clé pré-partagée (Pre-Shared Key) :

```bash
umask 277 && wg genpsk > /etc/wireguard/psk
```

*La clé pré-partagée (PresharedKey ou PSK) est une amélioration facultative de la sécurité conforme au protocole WireGuard. Il est recommandé d’utiliser une PSK unique par client pour renforcer la sécurité. En ajoutant une clé pré-partagée dans le processus, on améliore le mécanisme de chiffrement et d'authentification, ce qui réduit le risque d'attaques futures, notamment par des ordinateurs quantiques.*

- Récupérez la clé publique, la clé privé et la PSK et stockez-les temporairement dans un éditeur de texte :
```bash
cat /etc/wireguard/publickey
cat /etc/wireguard/privatekey
cat /etc/wireguard/psk
```

- Créez un fichier dans ```/etc/wireguard``` :

```bash
nano /etc/wireguard/wg0.conf
```

- Copiez ce contenu et remplacez la ligne ```PrivateKey``` par le contenu du fichier ```/etc/wireguard/privatekey``` :

```bash
[Interface]
Address = 10.0.0.1/32
ListenPort = 51820
PrivateKey = <Server wg0 PrivateKey>
```
### <span style="color:red;">Halte ! **Arrivé a cette étape vous devez d'abord configurer le client (étape X) et ensuite revenir sur le serveur pour finaliser la configuration.**
</span>

### Etape 3 - Finalisation de la configuration du serveur :
Vous allez maintenant ajouter votre client (Peer) sur le serveur pour l’autoriser à communiquer de manière sécurisée.

- Pour cela, ouvrez le fichier de configuration de WireGuard sur le serveur :

```sudo nano /etc/wireguard/wg0.conf```

- et ajoutez la partie suivante :

```bash
[Peer]
PublicKey = <Client wg0 public key>
PresharedKey = <Pre-Shared Key>
AllowedIPs = 10.0.0.2/32
PersistentKeepalive = 25
```

- Remplacez PublicKey par la clé publique du client que vous avez récupérée lors de la création du tunnel sur Windows 11, et la PresharedKey par celle du fichier /etc/wireguard/psk que vous avez créé sur le serveur.

>Rappel : Une PSK par client

- Modifiez la partie ```AllowedIPs```, et mettez l'IP privé de votre wg0 sur Windows 11 (dans mon exemple 10.0.0.2/32)

Votre fichier devrais ressembler a ceci :

![alt text](<Screenshots/2024-09-27 18_01_16-wg.png>)

Dans le cas ou vous voulez avoir une communication vers l'exterieur en utilisant votre VPN :

- Activer le routing en ajoutant/décommentant la ligne suivante dans le fichier ```/etc/sysctl.conf``` :

```net.ipv4.ip_forward=1```

- Rendez la configuration persistante avec la commande :

```bash
sudo sysctl -p
```

- Installez iptables ou une autre solution de pare-feu, puis configurez correctement la règle MASQUERADE.

Dans cet exemple, ens18 est mon interface qui fait office de carte réseau physique, et donc c'est à travers elle que les paquets transitent depuis/vers l'extérieur.

```bash
iptables -A FORWARD -i wg0 -o ens18 -j ACCEPT
iptables -t nat -A POSTROUTING -o ens18 -j MASQUERADE
```

- Ensuite et finalement vous activez l’interface wg0 :

```bash
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0
```

Félécitation ! Votre serveur VPN est maintenant configurer.

---

### Configuration du Client :
#### - Windows 11
#### Etape 1 - Installation

Téléchargez le binaire depuis le site WireGuard, et installer le.

#### Etape 2 - Configuration du client

- Lancez un editeur de texte.
- Lancez votre WireGuard.
  - Cliquez sur "Add Tunnel".
  - Choisissez "Add empty tunnel"
  
![alt text](<Screenshots/wireguard win10 add tunnel.jpg>)

Lorsque vous cliquez sur "Add empty tunnel" une nouvelle fenêtre apparaîtra. Gardez la partie suivante :

```bash
[Interface]
PrivateKey = xxxXxxXxXXXxXxxxx
```
- Sous ces informations, ajoutez les lignes ci dessous :

```bash
Address = 10.0.0.2/32
ListenPort = 51820

[Peer]
PublicKey = <Client wg0 public key>
PresharedKey = <Pre-Shared Key>
AllowedIPs = 0.0.0.0/1, 128.0.0.0/1
PersistentKeepalive = 25
Endpoint = <IP_publique_de_votre_serveur:port>
```

- Remplacez la partie ```PublicKey``` du Peer par la clé publique de votre serveur (celle copiée dans l'éditeur de texte précédemment), ainsi que la ```PresharedKey``` (PSK).
- Ajoutez également ```Endpoint```, qui est l'adresse IP publique de votre serveur ainsi que le port.
- Gardez les ```AllowedIPs``` comme dans l'exemple ; la gestion des communications sera réglée côté serveur. Si vous voulez limiter la communication uniquement au serveur, utilisez son IP privée, mais cela peut entraîner des bugs.
- Le ```PersistentKeepalive``` est reglé a 25 secondes, cela permet de garder une connexion active en la renouvellement toutes les 25 secondes.

Finalement votre fichier ressemblera donc a ceci :

```bash
[Interface]
PrivateKey = <Client wg0 Private Key>
Address = 10.0.0.2/32
ListenPort = 51820

[Peer]
PublicKey = <Server wg0 public key>
PresharedKey = <Pre-Shared Key>
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
Endpoint = <IP publique de votre serveur>
```

Avant de fermer la fenêtre, récupérez la clé publique du client et copiez-la dans votre éditeur de texte.

![alt text](<Screenshots/2024-09-27 15_56_43-Wireguard_screen-1.png>)

Donnez un nom à votre tunnel et sauvegardez-le.

Finaliser la configuration du serveur (étape 3 de la configuration du serveur), puis cliquez sur Activate pour vous connecter.

#### - MacOS

#### Etape 1 - Installation
- Télécharger WireGuard sur l'app store et installez-le sur votre Machine.
  
#### Etape 2 - Configuration

- Lancez WireGuarde depuis la barre de tâche et cliquez sur Gestion des tunnels: 
  
![alt text](<Screenshots/Capture d’écran 2024-09-28 à 14.48.01.png>)

- Cliquez sur le bouton + et faites Ajouter un tunnel video ...

![alt text](<Screenshots/Capture d’écran 2024-09-28 à 14.48.25.png>)


- Collez la configuration ci dessous, et modifiez selon vos paramètres.
*La partie PrivateKey est déjà pré-rempli ne la modifiez pas.*

- Copiez la clé publique affiché dans le client MacOS dans un editeur de texte.

Votre configuration devra ressembler a ceci :

![alt text](<Capture d’écran 2024-09-28 à 14.49.09.png>)

Donnez un nom à votre tunnel et sauvegardez-le.

Finaliser la configuration du serveur (étape 3 de la configuration du serveur), puis cliquez sur Activate pour vous connecter.

#### - Linux (Ubuntu)

#### Etape 1 - Installation
- Télécharger WireGuard en passant par les sources officielles d'Ubuntu :
  
```bash
sudo apt update
sudo apt install wireguard -y
```


#### Etape 2 - Configuration



- Copiez la clé publique affiché dans le client MacOS dans un editeur de texte.

Votre configuration devra ressembler a ceci :

![alt text](<Screenshots/Capture d’écran 2024-09-28 à 14.49.09.png>)

Donnez un nom à votre tunnel et sauvegardez-le.

Finaliser la configuration du serveur (étape 3 de la configuration du serveur), puis cliquez sur Activate pour vous connecter.




### Commandes utiles :

Arrêter l'interface wg0

```sudo wg-quick down wg0```

Redémarrer l'interface wg0 (uniquement après l'avoir down)

```sudo systemctl restart wg-quick@wg0```

Pour vérifier le status de l'interface wg0

```sudo systemctl status wg-quick@wg0```

>Si vous avez un serveur DNS au niveau de votre infrastructure vous pouvez le déclarer dans la partie [Interface] du serveur ainsi que le client. le serveur DNS doit être le même pour les deux.


