#!/bin/sh

docker build . -t hog_rida && \
	docker run -it hog_rida 
