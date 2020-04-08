# OpenFacsTrack
Software to track flow cytometry data.

## Deploy on Docker

```
git clone https://github.com/EBISPOT/OpenFacsTrack.git
cd OpenFacsTrack
make deploy
```

Go to [http://locahost:1337/admin](http://locahost:1337/admin).
## Install development environment

### Run development environment using Docker
#### Requirements

- Docker

#### Instructions
```
git clone https://github.com/EBISPOT/OpenFacsTrack.git
cd OpenFacsTrack
make dev
```
Go to [http://0.0.0.0:8000/admin](http://0.0.0.0:8000/admin/).
### Run development environment standalone

```
brew install postgresql
```


### Cleaning your environments

Run ```make help``` to see the cleaning environments goals.
