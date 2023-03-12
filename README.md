# Projet-5
Reconstruction de lignes caractéristiques par apprentissage dans les nuages de points 3D

https://www.mediafire.com/file/9o8fsdyctid0sk5/abc_test.7z/file  

https://www.mediafire.com/file/1lolinn1ehfxcl4/abc_test_3_4.hdf5/file

# Docker

```
bash docker/build_docker.sh
```

```
./docker/run_docker.sh -d data -l outputs -p 8888 -u
```

### Jupyter in Docker 

```
jupyter notebook --NotebookApp.token=abcd --ip=0.0.0.0 --port 8888 --no-browser
```
