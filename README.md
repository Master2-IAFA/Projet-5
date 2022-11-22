# Projet-5
Reconstruction de lignes caractéristiques par apprentissage dans les nuages de points 3D

https://www.mediafire.com/file/9o8fsdyctid0sk5/abc_test.7z/file  

https://www.mediafire.com/file/1lolinn1ehfxcl4/abc_test_3_4.hdf5/file

# Docker

```
sudo ./docker/build_docker.sh
```

```
sudo docker run --rm -it --name 3ddl.artonson.0.sharp_features -v {ton_path}/def:/code/ -p 8888:8888 artonson/sharp_features:latest
```

### Jupyter in Docker 

```
jupyter notebook --NotebookApp.token=abcd --ip=0.0.0.0 --port 8888 --no-browser
```
