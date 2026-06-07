MATCH (n) DETACH DELETE n;

MERGE (u:Identity {primary_identifier: 'username:jdoe@corp.local'}) SET u.name = 'jdoe';
MERGE (h:Asset {primary_identifier: 'hostname:SERVER01'}) SET h.name = 'SERVER01';
MERGE (ip:IOC {primary_identifier: 'ipv4:203.0.113.50'}) SET ip.value = '203.0.113.50';

MERGE (iOld:Incident {incident_id: 'INC-OLD-001'})
SET iOld.title = 'Phishing and C2', iOld.status = 'Closed', iOld.created_at = datetime() - duration('P5D');

MERGE (a090:Alert {alert_row_id: 'ALERT-090'})
SET a090.name = 'Suspicious email link', a090.status = 'closed', a090.risk_score = 55, a090.timestamp = datetime() - duration('P5D');
MERGE (a091:Alert {alert_row_id: 'ALERT-091'})
SET a091.name = 'Outbound C2 beacon', a091.status = 'closed', a091.risk_score = 65, a091.timestamp = datetime() - duration('P5D') + duration('PT25M');

MATCH (a090:Alert {alert_row_id: 'ALERT-090'})
MATCH (u:Identity {primary_identifier: 'username:jdoe@corp.local'})
MERGE (a090)-[:RELATED_TO]->(u);
MATCH (a090:Alert {alert_row_id: 'ALERT-090'})
MATCH (ip:IOC {primary_identifier: 'ipv4:203.0.113.50'})
MERGE (a090)-[:RELATED_TO]->(ip);
MATCH (a091:Alert {alert_row_id: 'ALERT-091'})
MATCH (ip:IOC {primary_identifier: 'ipv4:203.0.113.50'})
MERGE (a091)-[:RELATED_TO]->(ip);
MATCH (a090:Alert {alert_row_id: 'ALERT-090'})
MATCH (iOld:Incident {incident_id: 'INC-OLD-001'})
MERGE (a090)-[:PART_OF_INCIDENT]->(iOld);
MATCH (a091:Alert {alert_row_id: 'ALERT-091'})
MATCH (iOld:Incident {incident_id: 'INC-OLD-001'})
MERGE (a091)-[:PART_OF_INCIDENT]->(iOld);

MERGE (a099:Alert {alert_row_id: 'ALERT-099'})
SET a099.name = 'Unusual login', a099.status = 'open', a099.risk_score = 60, a099.timestamp = datetime() - duration('P2D');
MERGE (a101:Alert {alert_row_id: 'ALERT-101'})
SET a101.name = 'Suspicious RDP', a101.status = 'open', a101.risk_score = 75, a101.timestamp = datetime() - duration('P1D');
MERGE (a102:Alert {alert_row_id: 'ALERT-102'})
SET a102.name = 'PsExec lateral movement', a102.status = 'open', a102.risk_score = 78, a102.timestamp = datetime() - duration('PT20H');

MATCH (a099:Alert {alert_row_id: 'ALERT-099'})
MATCH (u:Identity {primary_identifier: 'username:jdoe@corp.local'})
MERGE (a099)-[:RELATED_TO]->(u);
MATCH (a099:Alert {alert_row_id: 'ALERT-099'})
MATCH (h:Asset {primary_identifier: 'hostname:SERVER01'})
MERGE (a099)-[:RELATED_TO]->(h);
MATCH (a101:Alert {alert_row_id: 'ALERT-101'})
MATCH (h:Asset {primary_identifier: 'hostname:SERVER01'})
MERGE (a101)-[:RELATED_TO]->(h);
MATCH (a101:Alert {alert_row_id: 'ALERT-101'})
MATCH (u:Identity {primary_identifier: 'username:jdoe@corp.local'})
MERGE (a101)-[:RELATED_TO]->(u);
MATCH (a102:Alert {alert_row_id: 'ALERT-102'})
MATCH (h:Asset {primary_identifier: 'hostname:SERVER01'})
MERGE (a102)-[:RELATED_TO]->(h);
MATCH (a102:Alert {alert_row_id: 'ALERT-102'})
MATCH (u:Identity {primary_identifier: 'username:jdoe@corp.local'})
MERGE (a102)-[:RELATED_TO]->(u);

MERGE (iMain:Incident {incident_id: 'demo-incident-1'})
SET iMain.title = 'Operation Shadow Login', iMain.status = 'open';

MATCH (a101:Alert {alert_row_id: 'ALERT-101'})
MATCH (iMain:Incident {incident_id: 'demo-incident-1'})
MERGE (a101)-[:PART_OF_INCIDENT]->(iMain);
MATCH (a102:Alert {alert_row_id: 'ALERT-102'})
MATCH (iMain:Incident {incident_id: 'demo-incident-1'})
MERGE (a102)-[:PART_OF_INCIDENT]->(iMain);

MATCH (a101:Alert {alert_row_id: 'ALERT-101'})
MATCH (a102:Alert {alert_row_id: 'ALERT-102'})
MERGE (a101)-[:CAUSED {
  confidence: 'chronological_sequence',
  time_delta_seconds: 900
}]->(a102);
