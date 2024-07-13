import os
import time
import requests
from dotenv import dotenv_values

config = dotenv_values(".env")
cwd = os.getcwd()

def cycle_through_getting_transcriptions(dict_of_jobs):
    for job, file in dict_of_jobs.values():
        status: str | None = check_job_watson_stt(job, file)
        match status:
            case "waiting" | "processing":
                pass
            case "failed":
                job_id: str | None = create_job_watson_stt(file)
                if job_id: dict_of_jobs[job_id] = file
            case "completed":
                del dict_of_jobs[job]
    return dict_of_jobs
    
# Reads an mp3 file and returns it as bytes
def read_mp3_file_as_bytes(file_name: str) -> bytes | None:
    file_path: str = f"{cwd}\\input_files\\{file_name}"
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file {file_name} does not exist at path {file_path}")
        
        with open(file_path, 'rb') as file:
            file_bytes: bytes = file.read()

        return file_bytes
    
    except FileNotFoundError as e:
        print(f"File not found: {e}")
    except PermissionError as e:
        print(f"Permission denied: {e}")
    except IOError as e:
        print(f"IO error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    return None

# Recivies a mp3 file, makes an api call to create a transcription job on ibm watson stt and returns the job_id
# https://cloud.ibm.com/apidocs/speech-to-text#createjob
def create_job_watson_stt(file_name: str) -> str | None:

    try:

        file_content_as_bytes: bytes = read_mp3_file_as_bytes(file_name)
        if not file_content_as_bytes:
            raise Exception(f"Create Job: Error reading the file {file_name} as bytes")
        
        model_name_stt: str = config["MODEL_NAME_STT"]
        
        endpoint_url: str = config["WATSON_STT_ENDPOINT_URL"]
        headers: dict = {
            "Content-Type": "audio/mp3"
        }
        
        response_create_job_watson_stt = requests.post(
            #url = f"{endpoint_url}/v1/recognitions?model={model_name_stt}&timestamps=true",
            url = f"{endpoint_url}/v1/recognitions?model={model_name_stt}",
            headers = headers,
            data = file_content_as_bytes,
            auth = ('apikey', config["WATSON_STT_API_KEY"])
        )
        
        # If an error occur, this method returns a HTTPError object
        response_create_job_watson_stt.raise_for_status()

        job_id: str = response_create_job_watson_stt.json()["id"]
        print(f"Job created for file {file_name} with id {job_id}")

        return job_id
    
    except requests.exceptions.HTTPError as e:
        print(f"Create Job: HTTP error occurred: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.ConnectionError as e:
        print(f"Create Job: Connection error occurred: {e}")
    except requests.exceptions.Timeout as e:
        print(f"Create Job: Timeout occurred: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Create Job: An error occurred while making the request: {e}")
    except KeyError as e:
        print(f"Create Job: Configuration key error: {e}")
    except Exception as e:
        print(f"Create Job: An unexpected error occurred: {e}")
    
    return None

# Recivies an job_id and file name, makes an api call to get the transcription job result from ibm watson stt
# If the job is completed it saves the file in output_files folder with the same name as the file
# https://cloud.ibm.com/apidocs/speech-to-text#checkjob
def check_job_watson_stt(job_id: str, file_name: str) -> str | None:

    endpoint_url: str = config["WATSON_STT_ENDPOINT_URL"]
    
    try:
    
        response_check_jobs_watson_stt = requests.get(
            url = f"{endpoint_url}/v1/recognitions/{job_id}",
            auth = ('apikey', config["WATSON_STT_API_KEY"])
        )

        # If an error occur, this method returns a HTTPError object
        response_check_jobs_watson_stt.raise_for_status()

        body_response_check_jobs_watson_stt = response_check_jobs_watson_stt.json()
    
    except requests.exceptions.HTTPError as e:
        print(f"Check Job: HTTP error occurred: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"Check Job: Connection error occurred: {e}")
        return None
    except requests.exceptions.Timeout as e:
        print(f"Check Job: Timeout occurred: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Check Job: An error occurred while making the request: {e}")
        return None
    except KeyError as e:
        print(f"Check Job: Configuration key error: {e}")
        return None
    except Exception as e:
        print(f"Check Job: An unexpected error occurred: {e}")
        return None
    
    match body_response_check_jobs_watson_stt["status"]:
        case "waiting" | "processing":
            print(f"Transcription of job {job_id} in progress")
            return "in progress"
        case "failed":
            print(f"Transcription of job {job_id} failed")
            return "failed"
        case "completed":
            print(f"Transcription of job {job_id} completed successfully")
            pass

    # If the job was successfull, save the transcript as a txt in the output_files folder

    transcription_result: str =  body_response_check_jobs_watson_stt["results"][0]["results"][0]["alternatives"][0]["transcript"]

    try:
        result_file_path: str = f"{cwd}\\output_files\\{file_name.split(".")[0]}.txt"
        with open(result_file_path, "w") as file:
            file.write(transcription_result)
            print(f"Text saved on {result_file_path}")
        
        return "success"
    
    except PermissionError as e:
        print(f"Permission denied: {e}")
    except IOError as e:
        print(f"IO error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
    return False

def main():
    
    path_input_files_folder: str = f"{cwd}\\input_files"
    
    # dict[job_id] = file_name
    dict_of_jobs: dict[str, str] = {}
    
    for files_to_transcribe in os.listdir(path_input_files_folder):
        file_name: str = files_to_transcribe.split("/")[-1]
        job_id: str | None = create_job_watson_stt(file_name)
        if job_id: dict_of_jobs[job_id] = file_name
        
    while(len(dict_of_jobs) > 0):
        dict_of_jobs = cycle_through_getting_transcriptions(dict_of_jobs)
        time.sleep(1)
    
    return None
        
    

if __name__ == "__main__":
    main()