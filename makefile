all: secrets/ca_key

secrets/ca_key: 
	mkdir -p secrets
	ssh-keygen -t rsa -b 4096 -f secrets/ca_key -N ""

clean:
	rm -rf secrets 
