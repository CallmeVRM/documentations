Aujourd’hui, on parle de deux types de trafic réseau : l'unicast et le broadcast.

Qu'est-ce que le Trafic Unicast ?

Le trafic unicast désigne une communication directe entre un appareil émetteur et un appareil récepteur spécifique. Contrairement à un broadcast qui enverra la trame vers tous les appareils.

Cela est parfaitement valide pour un Switch, mais il y a une petite nuance pour le HUB.

Je m'explique, 

La trame envoyé par PC1 avec l'adresse MAC 00:11:22:33:44:a5 à déstination de Serveur 1 avec l'adresse MAC 00:11:22:33:44:f6 sera traité différement si c'est un Switch ou un Hub

Dans le cas du Switch, la trame sera envoyé uniquement au port correspondant au serveur 1 (partant du principe que la table ARP du switch est configuré), alors que dans le cas du Hub, la trame sera envoyé à tous les ports, PC2 et PC3 receverons bien la trame, mais elle ne leur est pas destiné il vont tout simplement l'ignorer.

Et le Trafic Broadcast ?

Parfois, un ordinateur doit envoyer un message à tout le monde dans le réseau (DHCP par exemple). On appelle cela un broadcast. 
Dans ce cas, l'adresse MAC de destination est ff:ff:ff:ff:ff:ff, qui est une adresse spéciale utilisée pour cibler tous les appareils sur le réseau. 
Et pour le coup, les hubs et switches transmettent cette trame à chaque appareil connecté, sauf à celui qui l'a envoyée.

Petit point intéressant : si on utilise des switches gérés, on peut changer ce comportement en configurant des VLANs (Virtual LANs). En gros, cela permet de séparer virtuellement le réseau en différents segments, réduisant ainsi le nombre de machines concernées par un broadcast.

Pourquoi C'est Important ?

Même si les hubs sont aujourd'hui quasiment disparus des entreprises, il est toujours utile de comprendre le pricnipe de l'unicast et le broadcast qui vous seront utile lors du troubleshooting DHCP par exemple.