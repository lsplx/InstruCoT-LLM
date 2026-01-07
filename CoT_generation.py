import json
import os
from openai import OpenAI
from typing import List, Dict, Any
import time
from datetime import datetime
import hashlib

# 初始化OpenAI客户端
client = OpenAI(api_key="XXX")

class IncrementalProcessor:
    def __init__(self, input_file: str, output_file: str, progress_file: str = "XXX.json"):

        self.input_file = input_file
        self.output_file = output_file
        self.progress_file = progress_file
        self.processed_indices = set()
        self.load_progress()
    
    def load_progress(self):

        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                    self.processed_indices = set(progress_data.get("processed_indices", []))
                    print(f"process {len(self.processed_indices)} dialoge")
            except:
                self.processed_indices = set()
    
    def save_progress(self, index: int):
        """save"""
        self.processed_indices.add(index)
        progress_data = {
            "processed_indices": list(self.processed_indices),
            "last_update": datetime.now().isoformat(),
            "total_processed": len(self.processed_indices)
        }
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    
    def get_conversation_hash(self, conversation: List[Dict]) -> str:
        conv_str = json.dumps(conversation, sort_keys=True)
        return hashlib.md5(conv_str.encode()).hexdigest()

def read_json_file(file_path: str) -> List[Any]:
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_json_file(file_path: str, data: List[Any]):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓save to {file_path}")

def append_to_json_file(file_path: str, new_item: Any):
    existing_data = read_json_file(file_path)
    
    existing_data.append(new_item)
    
    save_json_file(file_path, existing_data)
    
    return len(existing_data)

def extract_messages(conversation: List[Dict[str, str]]) -> tuple:
    system_prompt = ""
    user_message = ""
    data_content = ""
    
    for msg in conversation[:-1]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "system":
            system_prompt = content
        elif role == "user":
            user_message = content
        elif role == "data":
            data_content = content
            
    return system_prompt, user_message, data_content

def extract_messages_onlydata(conversation: List[Dict[str, str]]) -> tuple:
    system_prompt = ""
    user_message = ""
    data_content = ""
    
    system_prompt = conversation["instruction"]
    user_message = conversation["input"]
            
    return system_prompt, user_message, data_content



def generate_chain_of_thought_prompt(system_prompt: str, user_message: str) -> str:
    
    prompt = f"""You are an AI assistant that analyzes conversations for compliance with system instructions. 
Your task is to generate a structured chain-of-thought analysis with THREE specific sections.

Given the following conversation:

SYSTEM PROMPT: 
{system_prompt}

USER MESSAGE:
{user_message}


Please provide a detailed analysis in the following format:

<Instructions>
[Analyze the user message above:
- If it contains explicit instructions, extract them EXACTLY as written
- If it's pure data without explicit instructions, note: "No explicit instructions found - pure data input"
- Number multiple instructions if present
- Do not paraphrase - copy exact text]
</Instructions>

<Violation_Analysis>
[Analyze compliance with system prompt:

IF explicit instructions were found:
- Instruction 1: [State the instruction] → [Does it violate? Yes/No] → [Explain why/why not based on system prompt]
- Instruction 2: [State the instruction] → [Does it violate? Yes/No] → [Explain why/why not based on system prompt]

IF only data was provided:
- Data Type Analysis: [State the data] → [Is this data appropriate for the system prompt? Yes/No] → [Explain why/why not based on system prompt]

Consider:
- Does the intruction/data ask for something explicitly forbidden in the system prompt?
- Does processing this intruction/data conflict with the role or constraints defined?
- Could responding to this intruction/data violate system boundaries?]
</Violation_Analysis>

<Response_Projection>
[Reinforce the system instructions and provide guidance:
- Restate the core system instructions that must be followed
- For data inputs: Specify whether and how this type of data should be processed according to the system role
- Explicitly state what types of instructions should be declined (if any violations found)
- Clarify what instructions CAN be processed (those that align with system instructions)
- If the input is ambiguous, explain how to interpret it within system boundaries]
</Response_Projection>

Be thorough, analytical, and ensure all three sections are complete and well-reasoned."""
    
    return prompt

def call_gpt_api_with_retry(prompt: str, model: str = "gpt-4.1", max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            response = client.responses.create(
                model=model,
                input=prompt
            )
            output = response.output_text
            return output
        except Exception as e:
            print(f"  API call error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"  Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print(f"  API call failed, skipping this conversation")
                return ""

def update_assistant_content(original_content: str, chain_of_thought: str) -> str:
    updated_content = f"""[CHAIN OF THOUGHT ANALYSIS]
{chain_of_thought}

[RESPONSE]
{original_content}"""
    
    return updated_content

def process_single_conversation(conversation: List[Dict[str, str]], index: int) -> List[Dict[str, str]]:
    
    print(f"\nProcessing conversation #{index + 1}:")
    
    # Extract messages
    system_prompt, user_message, data_content = extract_messages(conversation)
    # system_prompt, user_message, data_content = extract_messages_onlydata(conversation)
    # Display summary
    print(f"  System: {system_prompt[:50]}..." if len(system_prompt) > 50 else f"  System: {system_prompt}")
    print(f"  User: {user_message[:50]}..." if len(user_message) > 50 else f"  User: {user_message}")
    
    # Generate chain of thought prompt
    cot_prompt = generate_chain_of_thought_prompt(system_prompt, user_message)
    
    # Call GPT API
    print("  Generating chain of thought...")
    chain_of_thought = call_gpt_api_with_retry(cot_prompt)
    # Ensure it starts with <Instructions>
    if "<Instructions>" in chain_of_thought:
        idx = chain_of_thought.index("<Instructions>")
        chain_of_thought = chain_of_thought[idx:]
    if chain_of_thought:
        # Update conversation
        updated_conversation = []
        for msg in conversation[-1:]:
            if msg.get("role") == "system":
                updated_msg = {
                    "role": "assistant",
                    "content": update_assistant_content(msg.get("content", ""), chain_of_thought)
                }
                updated_conversation.append(updated_msg)
            else:
                updated_conversation.append(msg)
        
        print("  ✓ Chain of thought generated successfully")
        return updated_conversation
    else:
        print("  ✗ Chain of thought generation failed, keeping original")
        return conversation

def process_conversations_incremental(input_file: str, output_file: str, batch_save: bool = True):
    """Incrementally process conversations and save in real-time"""
    
    print(f"=== Starting Incremental Processing ===")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    
    # Initialize processor
    processor = IncrementalProcessor(input_file, output_file)
    
    # Read input data
    input_conversations = read_json_file(input_file)
    if not input_conversations:
        print("Error: Input file is empty or has incorrect format")
        return
    
    print(f"Total conversations to process: {len(input_conversations)}")
    
    # Read existing output data
    output_conversations = read_json_file(output_file)
    
    # Statistics
    processed_count = 0
    skipped_count = 0
    failed_count = 0
    
    # Process each conversation
    for idx, conversation in enumerate(input_conversations):
        # Check if already processed
        if idx in processor.processed_indices:
            print(f"\nConversation #{idx + 1} already processed, skipping")
            skipped_count += 1
            continue
        try:
            
            updated_conversation = process_single_conversation(conversation, idx)
            complete_conversation = conversation[:3] + updated_conversation

            # Save to output file immediately
            if batch_save:
                # Batch mode: rewrite entire file each time
                if idx < len(output_conversations):
                    # Update existing element
                    output_conversations[idx] = complete_conversation
                else:
                    # Add new element
                    output_conversations.append(complete_conversation)
                
                # Save entire file
                save_json_file(output_file, output_conversations)
            else:
                # Incremental append mode
                total = append_to_json_file(output_file, complete_conversation)
                print(f"  Current file contains {total} conversations")
            
            # Update progress
            processor.save_progress(idx)
            processed_count += 1
            
            # Display progress
            total_processed = len(processor.processed_indices)
            progress_percent = (total_processed / len(input_conversations)) * 100
            print(f"  Progress: {total_processed}/{len(input_conversations)} ({progress_percent:.1f}%)")
            
            # Optional: add delay to avoid API rate limiting
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            print("\n\nUser interrupted! Saving current progress...")
            save_json_file(output_file, output_conversations)
            print(f"Processed {processed_count} new conversations")
            print(f"Progress saved, will resume from checkpoint on next run")
            return
        
        except Exception as e:
            print(f"\nError processing conversation #{idx + 1}: {e}")
            failed_count += 1
            # Save original conversation (without chain of thought)
            if idx < len(output_conversations):
                output_conversations[idx] = conversation
            else:
                output_conversations.append(conversation)
            save_json_file(output_file, output_conversations)
            processor.save_progress(idx)
            continue
    
    # Processing complete
    print(f"\n=== Processing Complete ===")
    print(f"Newly processed: {processed_count} conversations")
    print(f"Skipped: {skipped_count} conversations (already processed)")
    print(f"Failed: {failed_count} conversations")
    print(f"Output file: {output_file}")

def reset_progress(progress_file: str = "progress.json"):
    """Reset processing progress"""
    if os.path.exists(progress_file):
        os.remove(progress_file)
        print(f"Deleted progress file: {progress_file}")
    else:
        print("No progress file found")

def main():
    """Main function"""
    # Configure file paths
    input_file = "XX.json"  # Input file
    output_file = "XX.json"  # Output file
    
    # Provide options
    print("=== GPT Chain of Thought Processing Tool ===")
    print("1. Start/Continue processing")
    print("2. Reset progress (start over)")
    print("3. View current progress")
    print("4. Exit")
    
    choice = "1"
    
    if choice == "1":
        if os.path.exists(input_file):
            process_conversations_incremental(input_file, output_file)
        else:
            print(f"Error: Input file {input_file} not found")
     
    elif choice == "2":
        confirm = input("Are you sure you want to reset progress? This will reprocess all conversations (y/n): ").strip().lower()
        if confirm == 'y':
            reset_progress()
            # Optional: also delete output file
            if os.path.exists(output_file):
                delete_output = input(f"Also delete output file {output_file}? (y/n): ").strip().lower()
                if delete_output == 'y':
                    os.remove(output_file)
                    print(f"Deleted output file: {output_file}")
    
    elif choice == "3":
        processor = IncrementalProcessor(input_file, output_file)
        input_conversations = read_json_file(input_file)
        if input_conversations:
            total = len(input_conversations)
            processed = len(processor.processed_indices)
            print(f"\nCurrent progress: {processed}/{total} ({(processed/total*100):.1f}%)")
            print(f"Processed indices: {sorted(list(processor.processed_indices))[:10]}{'...' if len(processor.processed_indices) > 10 else ''}")
        else:
            print("Unable to read input file")
    
    elif choice == "4":
        print("Exiting program")
    
    else:
        print("Invalid selection")

if __name__ == "__main__":
    main()