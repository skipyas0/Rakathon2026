# InterSystems IRIS for Health (Community) with our FHIR R4 endpoint at /fhir/r4.
# The endpoint is created on first start (setup.script via iris-main --after), so it lands in the
# durable data directory (ISC_DATA_DIRECTORY, a volume) and survives image upgrades.
FROM intersystems/irishealth-community:2026.1
COPY --chown=irisowner:irisowner setup.sh setup.script /home/irisowner/
COPY entrypoint.sh /entrypoint.sh
USER root
ENTRYPOINT ["/entrypoint.sh"]
CMD ["--after", "/home/irisowner/setup.sh"]
