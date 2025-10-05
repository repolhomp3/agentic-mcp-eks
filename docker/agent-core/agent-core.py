#!/usr/bin/env python3
import json
import sys
import boto3
import requests
from typing import Dict, List, Any
from http.server import HTTPServer, BaseHTTPRequestHandler

class AgentCore:
    def __init__(self):
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')
        self.mcp_endpoints = {
            'aws': 'http://aws-mcp-service:80',
            'database': 'http://database-mcp-service:80',
            'custom': 'http://custom-mcp-service:80',
            'k8s': 'http://k8s-mcp-service.k8s-admin:80'
        }
    
    def call_mcp_tool(self, server: str, tool: str, args: Dict) -> Dict:
        """Call MCP server tool"""
        url = self.mcp_endpoints.get(server)
        if not url:
            return {"error": f"Unknown MCP server: {server}"}
        
        payload = {
            "method": "tools/call",
            "params": {"name": tool, "arguments": args}
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def invoke_bedrock(self, prompt: str) -> str:
        """Invoke Bedrock model for reasoning"""
        try:
            response = self.bedrock.invoke_model(
                modelId='amazon.titan-text-lite-v1',
                body=json.dumps({
                    "inputText": prompt,
                    "textGenerationConfig": {"maxTokenCount": 200}
                })
            )
            result = json.loads(response['body'].read())
            return result['results'][0]['outputText']
        except Exception as e:
            return f"Bedrock error: {str(e)}"
    
    def execute_workflow(self, workflow: Dict) -> Dict:
        """Execute agentic workflow"""
        task = workflow.get('task', '')
        
        if 'bedrock' in task.lower():
            prompt = workflow.get('prompt', 'Hello from Agent Core!')
            result = self.invoke_bedrock(prompt)
            return {'workflow': 'bedrock_test', 'result': result}
        
        if 's3' in task.lower():
            result = self.call_mcp_tool('aws', 'list_s3_buckets', {})
            return {'workflow': 's3_list', 'result': result}
        
        if 'weather' in task.lower():
            city = workflow.get('city', 'San Francisco')
            # Multi-step workflow: Get weather -> Analyze -> Store
            weather = self.call_mcp_tool('custom', 'get_weather', {'city': city})
            analysis = self.invoke_bedrock(f"Analyze this weather: {weather}")
            storage = self.call_mcp_tool('custom', 'store_data', {
                'key': f'weather_{city}',
                'value': analysis
            })
            return {
                'workflow': 'weather_analysis',
                'steps': [
                    {'step': 'get_weather', 'result': weather},
                    {'step': 'ai_analysis', 'result': analysis},
                    {'step': 'store_result', 'result': storage}
                ]
            }
        
        if 'database' in task.lower():
            query = workflow.get('query', 'SELECT * FROM users')
            result = self.call_mcp_tool('database', 'execute_query', {'query': query})
            return {'workflow': 'database_query', 'result': result}
        
        if 'kubernetes' in task.lower() or 'k8s' in task.lower():
            if 'scale' in task.lower():
                deployment = workflow.get('deployment_name', 'agent-core')
                replicas = workflow.get('replicas', 3)
                result = self.call_mcp_tool('k8s', 'scale_deployment', {
                    'deployment_name': deployment,
                    'replicas': replicas
                })
                return {'workflow': 'k8s_scale', 'result': result}
            elif 'status' in task.lower() or 'health' in task.lower():
                result = self.call_mcp_tool('k8s', 'get_cluster_status', {})
                analysis = self.invoke_bedrock(f"Analyze this Kubernetes cluster status: {result}")
                return {
                    'workflow': 'k8s_health_check',
                    'steps': [
                        {'step': 'get_status', 'result': result},
                        {'step': 'ai_analysis', 'result': analysis}
                    ]
                }
            elif 'pods' in task.lower():
                namespace = workflow.get('namespace', 'default')
                result = self.call_mcp_tool('k8s', 'list_pods', {'namespace': namespace})
                return {'workflow': 'k8s_list_pods', 'result': result}
            elif 'troubleshoot' in task.lower():
                pod_name = workflow.get('pod_name')
                if pod_name:
                    result = self.call_mcp_tool('k8s', 'troubleshoot_pod', {'pod_name': pod_name})
                    analysis = self.invoke_bedrock(f"Provide troubleshooting recommendations: {result}")
                    return {
                        'workflow': 'k8s_troubleshoot',
                        'steps': [
                            {'step': 'analyze_pod', 'result': result},
                            {'step': 'ai_recommendations', 'result': analysis}
                        ]
                    }
                return {'error': 'pod_name required for troubleshooting'}
            else:
                result = self.call_mcp_tool('k8s', 'get_cluster_status', {})
                return {'workflow': 'k8s_general', 'result': result}
        
        if 'glue' in task.lower():
            if 'start' in task.lower():
                job_name = workflow.get('job_name', 'my-etl-job')
                # Multi-step: Start job -> Monitor -> Report
                start_result = self.call_mcp_tool('aws', 'start_glue_job', {'job_name': job_name})
                
                # Extract run_id for monitoring
                try:
                    run_data = json.loads(start_result['content'][0]['text'])
                    run_id = run_data['run_id']
                    
                    # Get initial status
                    status_result = self.call_mcp_tool('aws', 'get_glue_job_status', {
                        'job_name': job_name,
                        'run_id': run_id
                    })
                    
                    # AI analysis of job execution
                    analysis = self.invoke_bedrock(f"Analyze this Glue job execution: {status_result}")
                    
                    return {
                        'workflow': 'glue_job_execution',
                        'steps': [
                            {'step': 'start_job', 'result': start_result},
                            {'step': 'check_status', 'result': status_result},
                            {'step': 'ai_analysis', 'result': analysis}
                        ]
                    }
                except Exception as e:
                    return {'workflow': 'glue_job_execution', 'error': str(e)}
            else:
                # List jobs workflow
                jobs_result = self.call_mcp_tool('aws', 'list_glue_jobs', {})
                analysis = self.invoke_bedrock(f"Analyze these Glue jobs and suggest optimizations: {jobs_result}")
                
                return {
                    'workflow': 'glue_jobs_analysis',
                    'steps': [
                        {'step': 'list_jobs', 'result': jobs_result},
                        {'step': 'ai_analysis', 'result': analysis}
                    ]
                }
        
        return {"error": "Unknown workflow"}

class AgentHandler(BaseHTTPRequestHandler):
    def __init__(self, agent_core, *args, **kwargs):
        self.agent_core = agent_core
        super().__init__(*args, **kwargs)
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            request = json.loads(post_data.decode('utf-8'))
            method = request.get('method')
            
            if method == 'workflow/execute':
                result = self.agent_core.execute_workflow(request.get('params', {}))
            else:
                result = {"error": "Unknown method"}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        elif self.path == '/metrics':
            # Simple Prometheus metrics
            metrics = '''# HELP agent_core_requests_total Total requests processed
# TYPE agent_core_requests_total counter
agent_core_requests_total 42
# HELP agent_core_active_workflows Active workflows
# TYPE agent_core_active_workflows gauge
agent_core_active_workflows 3
'''
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(metrics.encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == "__main__":
    agent = AgentCore()
    
    def handler(*args, **kwargs):
        AgentHandler(agent, *args, **kwargs)
    
    httpd = HTTPServer(('0.0.0.0', 8000), handler)
    print("Agent Core running on port 8000")
    httpd.serve_forever()