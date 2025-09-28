#!/usr/bin/env python3
import json
import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class AWSMCP:
    def __init__(self):
        self.session = None
        self.init_aws_session()
    
    def init_aws_session(self):
        try:
            self.session = boto3.Session()
            sts = self.session.client('sts')
            sts.get_caller_identity()
        except (NoCredentialsError, ClientError):
            self.session = None
    
    def handle_request(self, request):
        method = request.get('method')
        params = request.get('params', {})
        
        if method == 'tools/list':
            return {
                "tools": [
                    {
                        "name": "list_s3_buckets",
                        "description": "List S3 buckets",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "invoke_bedrock_model",
                        "description": "Invoke Bedrock model",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "prompt": {"type": "string", "description": "Text prompt"},
                                "max_tokens": {"type": "integer", "default": 100}
                            },
                            "required": ["prompt"]
                        }
                    },
                    {
                        "name": "list_glue_jobs",
                        "description": "List AWS Glue jobs",
                        "inputSchema": {"type": "object", "properties": {}}
                    },
                    {
                        "name": "start_glue_job",
                        "description": "Start a Glue job run",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "job_name": {"type": "string", "description": "Glue job name"}
                            },
                            "required": ["job_name"]
                        }
                    },
                    {
                        "name": "get_glue_job_status",
                        "description": "Get Glue job run status",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "job_name": {"type": "string", "description": "Glue job name"},
                                "run_id": {"type": "string", "description": "Job run ID"}
                            },
                            "required": ["job_name", "run_id"]
                        }
                    }
                ]
            }
        
        elif method == 'tools/call':
            if not self.session:
                return {"error": "AWS credentials not configured"}
            
            tool_name = params.get('name')
            args = params.get('arguments', {})
            
            if tool_name == 'list_s3_buckets':
                return self.list_s3_buckets()
            elif tool_name == 'invoke_bedrock_model':
                return self.invoke_bedrock_model(args['prompt'], args.get('max_tokens', 100))
            elif tool_name == 'list_glue_jobs':
                return self.list_glue_jobs()
            elif tool_name == 'start_glue_job':
                return self.start_glue_job(args['job_name'])
            elif tool_name == 'get_glue_job_status':
                return self.get_glue_job_status(args['job_name'], args['run_id'])
        
        return {"error": "Unknown method"}
    
    def list_s3_buckets(self):
        try:
            s3 = self.session.client('s3')
            response = s3.list_buckets()
            buckets = [bucket['Name'] for bucket in response['Buckets']]
            return {"content": [{"type": "text", "text": f"S3 Buckets: {json.dumps(buckets)}"}]}
        except Exception as e:
            return {"error": f"S3 error: {str(e)}"}
    
    def invoke_bedrock_model(self, prompt, max_tokens):
        try:
            bedrock = self.session.client('bedrock-runtime', region_name='us-west-2')
            body = {
                "inputText": prompt,
                "textGenerationConfig": {"maxTokenCount": min(max_tokens, 100)}
            }
            
            response = bedrock.invoke_model(
                modelId='amazon.titan-text-lite-v1',
                body=json.dumps(body)
            )
            
            result = json.loads(response['body'].read())
            output_text = result['results'][0]['outputText']
            
            return {"content": [{"type": "text", "text": output_text}]}
        except Exception as e:
            return {"error": f"Bedrock error: {str(e)}"}
    
    def list_glue_jobs(self):
        try:
            glue = self.session.client('glue', region_name='us-west-2')
            response = glue.get_jobs()
            jobs = [{
                "name": job['Name'],
                "role": job['Role'],
                "created": job['CreatedOn'].isoformat() if 'CreatedOn' in job else None,
                "last_modified": job['LastModifiedOn'].isoformat() if 'LastModifiedOn' in job else None
            } for job in response['Jobs']]
            return {"content": [{"type": "text", "text": json.dumps(jobs, indent=2)}]}
        except Exception as e:
            return {"error": f"Glue error: {str(e)}"}
    
    def start_glue_job(self, job_name):
        try:
            glue = self.session.client('glue', region_name='us-west-2')
            response = glue.start_job_run(JobName=job_name)
            result = {
                "job_name": job_name,
                "run_id": response['JobRunId'],
                "status": "STARTING"
            }
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
        except Exception as e:
            return {"error": f"Glue job start error: {str(e)}"}
    
    def get_glue_job_status(self, job_name, run_id):
        try:
            glue = self.session.client('glue', region_name='us-west-2')
            response = glue.get_job_run(JobName=job_name, RunId=run_id)
            job_run = response['JobRun']
            result = {
                "job_name": job_name,
                "run_id": run_id,
                "state": job_run['JobRunState'],
                "started_on": job_run['StartedOn'].isoformat() if 'StartedOn' in job_run else None,
                "completed_on": job_run['CompletedOn'].isoformat() if 'CompletedOn' in job_run else None,
                "execution_time": job_run.get('ExecutionTime', 0)
            }
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
        except Exception as e:
            return {"error": f"Glue job status error: {str(e)}"}

class MCPHandler(BaseHTTPRequestHandler):
    def __init__(self, mcp_server, *args, **kwargs):
        self.mcp_server = mcp_server
        super().__init__(*args, **kwargs)
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            request = json.loads(post_data.decode('utf-8'))
            response = self.mcp_server.handle_request(request)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')

if __name__ == "__main__":
    server = AWSMCP()
    
    def handler(*args, **kwargs):
        MCPHandler(server, *args, **kwargs)
    
    httpd = HTTPServer(('0.0.0.0', 8000), handler)
    print("AWS MCP Server running on port 8000")
    httpd.serve_forever()