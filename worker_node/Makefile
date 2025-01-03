GCP_PROJECT_ID = tcc-mt
GCP_APPLICATION_NAME = machine-teaching-worker

IMAGE_DESTINATION = gcr.io/$(GCP_PROJECT_ID)/$(GCP_APPLICATION_NAME)

# GIT COMMIT ID
VERSION=$(shell (git rev-parse HEAD))

deploy:
	@echo "Version ID: $(VERSION)";
	docker build --tag $(IMAGE_DESTINATION):$(VERSION) .
	docker push $(IMAGE_DESTINATION):$(VERSION)
	@echo "Image submitted to destination repository :)"
		
run-docker:
	docker build --tag $(IMAGE_DESTINATION):$(VERSION) .
	docker run -it --env PORT=5000 -p 5000:5000 $(IMAGE_DESTINATION):$(VERSION)
