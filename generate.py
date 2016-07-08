#!/usr/bin/env python
# run as:
# ./generate.py -f topology.dot -p client/producer/test.cfg -c client/consumer/test.cfg 

import sys
import os
import shutil
import getopt
import re
import copy
import pygraphviz as pgv
import pylibconfig2 as cfglib
import yaml
# install from https://github.com/peetonn/dockerfile-parse
from dockerfile_parse import DockerfileParser

graphNodes = {}

def usage():
	print "usage: "+sys.argv[0]+" -f <dotfile> -p <producer_config> -c <consumer_config>"
	print ""

def loadConf(confFile):
	with open(confFile) as f:
		config = cfglib.Config(f.read())
	return config

def loadBaseYml():
	baseYml = 'base.yml'
	with open(baseYml) as f:
		yml = yaml.safe_load(f)
		yml['services'] = {}
	return yml

def parseConsumerLabel(label):
	p = re.compile('C\d+x(?P<cluster_size>\d+)\s*<-\s*(?P<fetch_from>(P\d+\s*)+)')
	m = p.match(label)
	if m:
		clusterSize = int(m.group('cluster_size'))
		fetchFrom = m.group('fetch_from')
		producers = []
		for mm in re.finditer(r'P\d+', fetchFrom):
			producers.append(mm.group(0))
		return clusterSize, producers
	print "consumer cluster label was not recognized"
	return None, None

def createConsumerNodes(node):
	index = int(node.name[1:])
	if 'label' in node.attr.keys():
		label = node.attr['label']
		clusterSize, fetchFrom = parseConsumerLabel(label)
		if clusterSize:
			nodes = []
			for i in range(0,clusterSize):
				nodes.append({
								'service':'consumer'+str(index)+'_'+str(i), 
								'type':'consumer',
								'cluster_index':index,
								'index':i,
								'fetch_from': fetchFrom
							})
			return nodes
	else:
		print "consuer cluster node "+node.name+" doesn't have label attribute"
	return None

def createGraphNode(node):
	nodeMark = node.name.lower()[0]
	index = int(node.name[1:])
	graphNodes = {
			'h':{'service':'hub'+str(index), 'type':'hub', 'index':index, 'node':node},
			'p':{'service':'producer'+str(index), 'type':'producer', 'index':index, 'node':node}
		}
	if not nodeMark in graphNodes.keys():
		if nodeMark == 'c':
			nodes = createConsumerNodes(node)
			if nodes:
				return {'type':'cluster', 'nodes':nodes, 'node':node, 'index':index}
		print "unrecognized node "+node.name
		return None
	else:
		return graphNodes[nodeMark]

def getGraphNodes(nodeType):
	global graphNodes
	nodes = []
	for node in graphNodes.keys():
		if nodeType == 'consumer':
			if graphNodes[node]['type'] == 'cluster':
				nodes.extend(graphNodes[node]['nodes'])
		elif graphNodes[node]['type'] == nodeType:
			nodes.append(graphNodes[node])
	return nodes

def getGraphNodeByServiceName(serviceName):
	global graphNodes
	for node in graphNodes.keys():
		if graphNodes[node]['type'] != 'cluster':
			if graphNodes[node]['service'] == serviceName:
				return graphNodes[node]
		else:
			for consumerNode in graphNodes[node]['nodes']:
				if consumerNode['service'] == serviceName:
					return consumerNode
	return None

def parseNodes(graph):
	global graphNodes
	for node in graph.nodes():
		graphNode = createGraphNode(node)
		if graphNode:
			graphNodes[node.name] = graphNode

def createTestFolder():
	testNo = 1
	while os.path.exists("./test"+str(testNo)):
		testNo += 1
	d = "./test"+str(testNo)
	os.makedirs(d)
	return d

def makeClientContext(pdir, index, clientType):
	clidirName = clientType[0]+str(index)
	clidir = os.path.join(pdir, clidirName)
	os.makedirs(clidir)
	clicfg = os.path.join(clidir, 'test.cfg')
	shutil.copyfile('./client/'+clientType+'/test.cfg', clicfg)
	clirun = os.path.join(clidir, 'runtest.sh')
	shutil.copyfile('./client/runtest.sh', clirun)
	return clidirName 

def makeHubContext(pdir):
	hubdirName = 'hub'
	hubdir = os.path.join(pdir, hubdirName)
	os.makedirs(hubdir)
	hubrun = os.path.join(hubdir, 'runtest.sh')
	shutil.copyfile('./hub/runtest.sh', hubrun)
	hubdocker = os.path.join(hubdir, 'Dockerfile')
	shutil.copyfile('./hub/Dockerfile', hubdocker)
	return hubdirName

def updateProducerCfg(config, node):
	try:
		basePrefix = config.produce.basic.prefix
		config.produce.basic.username = node['service']
		for stream in config.produce.streams:
			stream.session_prefix = basePrefix+'/ndnrtc/user/'+node['service']
		return config
	except Exception as e:
		print "error while reading config file for "+node['service']+": "+str(e)

def updateConsumerCfg(config, node):
	global graphNodes
	fetchFrom = node['nodes'][0]['fetch_from']
	stream = copy.copy(config.consume.streams[0])
	thread = copy.copy(stream.threads[0])
	while len(config.consume.streams): del config.consume.streams[0]
	for p in fetchFrom:
		pcfg = loadConf(graphNodes[p]['config'])
		for s in pcfg.produce.streams:
			consumeStream = copy.copy(stream)
			while len(consumeStream.threads): del consumeStream.threads[0]
			consumeStream.session_prefix = s.session_prefix
			consumeStream.name = s.name
			consumeStream.thread_to_fetch = s.threads[0].name
			for t in s.threads:
				consumeThread = copy.copy(thread)
				consumeThread.name = t.name
				consumeThread.coder = t.coder
				consumeStream.threads.append(consumeThread)
			config.consume.streams.append(consumeStream)
	return config

def updateCfg(cfg, type, node, outfile):
	global graphNodes 
	if type == 'producer': 
		cfg = updateProducerCfg(cfg, node)
	else: 
		cfg = updateConsumerCfg(cfg, node)
	graphNodes[node['node'].name]['config'] = outfile
	with open(outfile, 'w') as f:
		f.write(str(cfg))

def getConnectedNodes(graph, node):
	global graphNodes
	dependencies =[]
	for neighbor in graph.neighbors_iter(node):
		if neighbor.name in graphNodes.keys():
			dependencies.append(graphNodes[neighbor.name])
	return dependencies

def createClientDockerfile(dir):
	base = './client/Dockerfile-base'
	if os.path.exists(base):
		dockerfile = os.path.join(dir, 'Dockerfile')
		shutil.copyfile(base, dockerfile)

def producerCmd(serviceName, hub):
	node = getGraphNodeByServiceName(serviceName)
	if node:
		cluster = 'p'+str(node['index'])
		return "/root/headless/runtest.sh "+serviceName+" "+hub+" "+cluster+" $RUNTIME $TAGS"
	return None

def generateProducers(yml, graph, config, pdir):
	global graphNodes
	for k in graphNodes.keys():
		if graphNodes[k]['type'] == 'producer':
			node = graphNodes[k]
			hubs = getConnectedNodes(graph, k)
			context = makeClientContext(pdir, node['index'], 'producer')
			createClientDockerfile(os.path.join(pdir, context))
			updateCfg(config, 'producer', node, os.path.join(pdir, context, 'test.cfg'))
			producerYml = {
							'build': context,
							'container_name':node['service'],
							'networks':['local-testbed'],
							'command': producerCmd(node['service'], hubs[0]['service'])
						}
			if len(hubs):
				producerYml['depends_on'] = [h['service'] for h in hubs]
			yml['services'][node['service']] = producerYml

def hubCmd(serviceName, connected):
	return "/root/headless/runtest.sh "+serviceName+' "'+" ".join(connected)+'" $RUNTIME $TAGS'

def generateHubs(yml, graph, pdir):
	global graphNodes
	hubs = getGraphNodes('hub')
	context = makeHubContext(pdir)
	for node in hubs:
		connected = getConnectedNodes(graph, node['node'])
		hubProducersConnected = [c['service'] for c in connected if c['type'] != 'cluster']
		hubYml = {
					'build': context,
					'container_name':node['service'],
					'networks':['local-testbed'],
					'command': hubCmd(node['service'], hubProducersConnected)
				}
		yml['services'][node['service']] = hubYml

def consumerCmd(serviceName, cluster, hubs):
	return "/root/headless/runtest.sh "+serviceName+' "'+" ".join(hubs)+'" "'+cluster+'" $RUNTIME $TAGS'

def generateConsumers(yml, graph, config, pdir):
	global graphNodes
	consumerClusters = getGraphNodes('cluster')
	for cluster in consumerClusters:
		context = makeClientContext(pdir, cluster['index'], 'consumer')
		createClientDockerfile(os.path.join(pdir, context))
		updateCfg(copy.copy(config), 'consumer', cluster, os.path.join(pdir, context, 'test.cfg'))
		connected = getConnectedNodes(graph, cluster['node'].name)
		producers = [graphNodes[k] for k in cluster['nodes'][0]['fetch_from']]
		dependencies = connected+producers
		for consumer in cluster['nodes']:
			consumerYml = {
							'build': context,
							'container_name':consumer['service'],
							'depends_on':[h['service'] for h in dependencies],
							'networks':['local-testbed'],
							'command':consumerCmd(consumer['service'], str(cluster['node'].name), [h['service'] for h in connected])
						}
			yml['services'][consumer['service']] = consumerYml

def saveYml(dir, yml):
	with open(os.path.join(dir,'docker-compose.yml'), 'w') as f:
		f.write(yaml.dump({'version':yml['version']}, default_flow_style=False))
		f.write(yaml.dump({'services':yml['services']}, default_flow_style=False))
		f.write(yaml.dump({'networks':yml['networks']}, default_flow_style=False))

def generate(dotFile, producerConf, consumerConf):
	toplogy = pgv.AGraph(dotFile)
	pcfg = loadConf(producerConf)
	ccfg = loadConf(consumerConf)
	yml = loadBaseYml()
	parseNodes(toplogy)
	
	# create parent folder 
	pdir = createTestFolder()
	# generate hubs
	generateHubs(yml, toplogy, pdir)
	# generate producers
	generateProducers(yml, toplogy.subgraph(name='producers'), pcfg, pdir)
	# generate consumers
	generateConsumers(yml, toplogy.subgraph(name='consumers'), ccfg, pdir)
	shutil.copyfile('run-compose.sh', os.path.join(pdir, 'run-compose.sh'))
	saveYml(pdir, yml)

def main():
	try:
		opts, args = getopt.getopt(sys.argv[1:], "f:p:c:", 
			["file=", "producer=", "consumer="])
	except getopt.GetoptError as err:
		print str(err)
		usage()
		exit(2)

	dotFile=None
	producerConfig=None
	consumerConfig=None
	for o,a in opts:
		if o in ("-f", "--file"):
			dotFile = a
		elif o in ("-p", "--producer"):
			producerConfig = a
		elif o in ("-c", "--consumer"):
			consumerConfig = a
		else:
			assert False, "unhandled option "+o
	if not (dotFile and producerConfig and consumerConfig):
		usage()
		exit(2)

	generate(dotFile, producerConfig, consumerConfig)


if __name__ == '__main__':
	main()