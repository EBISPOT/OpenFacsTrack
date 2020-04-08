default: dev

dev:            ##@dev setup development environment using Docker
	chmod +x entrypoint.dev.sh
	docker-compose -f docker-compose.dev.yml up --build

clean-dev:          ##@clean-dev clean development environment containers
	docker-compose -f docker-compose.dev.yml down

deploy:         ##@deploy setup production environment using Docker
	chmod +x entrypoint.prod.sh
	docker-compose -f docker-compose.prod.yml up --build

clean-deploy:      ##@clean-deploy clean production environment containers
	docker-compose -f docker-compose.prod.yml down

########################################################################################################################
 HELP_FUN = \
		 %help; \
		 while(<>) { push @{$$help{$$2 // 'options'}}, [$$1, $$3] if /^(\w+\-*\w*)\s*:.*\#\#(?:@(\w+\-*\w*))?\s(.*)$$/ }; \
		 print "usage: make [target]\n\n"; \
	 for (keys %help) { \
		 print "$$_:\n"; $$sep = " " x (5 - length $$_->[0]); \
		 print "  $$_->[0]$$sep$$_->[1]\n" for @{$$help{$$_}}; \
		 print "\n"; }


help:
	@echo "Run 'make' without a target to run the development environment using Docker \n"
	@perl -e '$(HELP_FUN)' $(MAKEFILE_LIST)