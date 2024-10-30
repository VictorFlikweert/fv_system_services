# Define all the collector targets
TARGETS = backup_collector log_collector machine_data_collector \
          meter_reading_collector meter_reading_rmq_collector \
          meter_reading_rmq_history_collector rmq_executer

# Define 'build' to depend on all individual targets
build: $(TARGETS)

# .PHONY tells make that these targets don't correspond to actual files
.PHONY: build $(TARGETS)

# Pattern rule to build each target using its Dockerfile
$(TARGETS):
	docker build --build-arg TARGET_NAME=$@ -t $@ -f Dockerfile .
	docker tag $@ flikweertvision/$@:latest
	docker push flikweertvision/$@:latest
