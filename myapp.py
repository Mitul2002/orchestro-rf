from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional
import pandas as pd

app = FastAPI()

# Define the file path for the contract data
file_path = '/home/miso/Documents/werk/Contract Discounts (2).xlsx'

# Functions from the previous logic
def select_carrier_and_spend(carrier_name, annual_spend, tolerance=0.1):
    return process_contracts(file_path, carrier_name, annual_spend, tolerance)

def get_top_service_types(contracts_df, top_n=10):
    common_service_types = contracts_df['Service Level'].value_counts().nlargest(top_n).index
    filtered_contracts = contracts_df[contracts_df['Service Level'].isin(common_service_types)]
    return filtered_contracts

def display_discount_data(filtered_contracts):
    discount_summary = clean_and_summarize(filtered_contracts)
    return discount_summary

def process_contracts(file_path, input_carrier, input_annual_spend, tolerance):
    xls = pd.ExcelFile(file_path)
    relevant_contracts = []
    for sheet_name in xls.sheet_names:
        if input_carrier.lower() in sheet_name.lower():
            spend_str = sheet_name.split('$')[-1].replace('M', '').replace('K', '')
            multiplier = 1_000_000 if 'M' in sheet_name else 1_000
            contract_spend = float(spend_str) * multiplier
            if abs(contract_spend - input_annual_spend) / input_annual_spend <= tolerance:
                sheet_df = pd.read_excel(file_path, sheet_name=sheet_name)
                cleaned_df = clean_contract_data(sheet_df)
                relevant_contracts.append(cleaned_df)
    if relevant_contracts:
        combined_contracts = pd.concat(relevant_contracts)
        common_service_types = combined_contracts['Service Level'].value_counts().nlargest(10).index
        filtered_contracts = combined_contracts[combined_contracts['Service Level'].isin(common_service_types)]
        return filtered_contracts
    else:
        return pd.DataFrame()

def clean_contract_data(df):
    df_cleaned = df.iloc[:, :3]
    df_cleaned.columns = ['Service Level', 'Weight Range', 'Discount Rate']
    df_cleaned = df_cleaned.dropna(subset=['Service Level', 'Discount Rate'])
    return df_cleaned

def clean_and_summarize(contracts_df):
    contracts_df['Discount Rate'] = pd.to_numeric(contracts_df['Discount Rate'], errors='coerce')
    contracts_df = contracts_df.dropna(subset=['Discount Rate'])
    summary = contracts_df.groupby('Service Level')['Discount Rate'].agg(['mean', 'min', 'max', 'count']).reset_index()
    summary.columns = ['Service Level', 'Average Discount', 'Min Discount', 'Max Discount', 'Contracts Count']
    return summary


# Define the request model
class ContractQuery(BaseModel):
    carrier: str
    annual_spend: float
    top_n_service_types: Optional[int] = 10
    tolerance: Optional[float] = 0.1

# Define the API endpoint
@app.post("/get-discounts/")
def get_discounts(query: ContractQuery):
    # Step 1: Select carrier and annual spend with adjustable range
    filtered_contracts = select_carrier_and_spend(query.carrier, query.annual_spend, tolerance=query.tolerance)
    
    if filtered_contracts.empty:
        return {"error": f"No contracts found for {query.carrier} with annual spend around {query.annual_spend}."}
    
    # Step 2: Get top service types (5-10)
    top_service_types_contracts = get_top_service_types(filtered_contracts, top_n=query.top_n_service_types)

    # Step 3: Display discount data
    discount_data = display_discount_data(top_service_types_contracts)
    
    # Return the summary as JSON response
    return discount_data.to_dict(orient="records")
