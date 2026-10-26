.PHONY: backup check restore-test retention-preview retention-apply health monitoring-up validate
backup:
	sudo systemctl start naslab-backup.service
check:
	sudo systemctl start naslab-verify.service
restore-test:
	sudo systemctl start naslab-restore-test.service
retention-preview:
	sudo python3 /opt/naslab/naslab.py retention
retention-apply:
	sudo systemctl start naslab-maintenance.service
health:
	sudo python3 /opt/naslab/naslab.py healthcheck
monitoring-up:
	sudo docker compose --env-file /etc/naslab/monitoring.env -f monitoring/compose.yml up -d
validate:
	python3 -m unittest discover -s tests/unit -v
	bash -n infrastructure/provision.sh
