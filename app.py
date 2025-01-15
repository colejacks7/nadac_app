import pandas as pd
import streamlit as st

def process_files_with_adjusted_filtering(top_100_data, nadac_data, reimbursement_data):
    """
    Process the Top 100, NADAC, and reimbursement files to generate a final output file.
    Includes adjusted filtering logic for missing network values and additional error handling.
    """
    # Ensure required columns exist
    required_columns = {
        "Top 100": ["NDC", "Drug"],
        "NADAC": ["NDC", "NADAC Per Unit"],
        "Reimbursement": ["Dispensed Item NDC", "Primary Remit Amount"]
    }

    for file_name, columns in required_columns.items():
        for column in columns:
            if column not in eval(f"{file_name.lower().replace(' ', '_')}_data").columns:
                st.error(f"{file_name} file must contain '{column}' column.")
                st.stop()

    # Standardize NDC formatting
    top_100_data["NDC"] = top_100_data["NDC"].astype(str).str.zfill(11)
    nadac_data["NDC"] = nadac_data["NDC"].astype(str).str.zfill(11)
    reimbursement_data["Dispensed Item NDC"] = (
        reimbursement_data["Dispensed Item NDC"]
        .astype(str)
        .str.split('.')
        .str[0]
        .str.zfill(11)
    )

    # Filter out rows with invalid remit amounts but allow missing network values
    valid_reimbursement_data = reimbursement_data[
        reimbursement_data["Primary Remit Amount"].fillna(0) > 0
    ]

    # Create a lookup dictionary for NADAC prices
    nadac_lookup = nadac_data.set_index("NDC")["NADAC Per Unit"].to_dict()

    # Create a list to store the output rows
    output_rows = []

    # Process each row in the Top 100 data
    for _, row in top_100_data.iterrows():
        ndc = row["NDC"]
        drug_name = row["Drug"]

        # Lookup NADAC price
        nadac_price = nadac_lookup.get(ndc, None)

        # Lookup reimbursement data
        reimbursement_match = valid_reimbursement_data[valid_reimbursement_data["Dispensed Item NDC"] == ndc]
        if not reimbursement_match.empty:
            # Take the row with the highest Primary Remit Amount
            best_match = reimbursement_match.sort_values(by="Primary Remit Amount", ascending=False).iloc[0]
            bin_code = best_match.get("Primary Third Party Bin", "Not Available")
            pcn = best_match.get("Primary Third Party PCN", "Not Available")
            network = best_match.get("Primary Network Reimbursement", "Not Available")
            reimbursement = best_match.get("Primary Remit Amount", 0.0)
        else:
            bin_code = "Not Available"
            pcn = "Not Available"
            network = "Not Available"
            reimbursement = 0.0

        # Append the row to output
        output_rows.append({
            "Drug Name": drug_name,
            "NDC": ndc,
            "NADAC": nadac_price,
            "Bin": bin_code,
            "PCN": pcn,
            "Network": network,
            "Reimbursement": reimbursement,
            "Price": None,  # Blank Price column
        })

    # Convert the output rows into a DataFrame
    output_data = pd.DataFrame(output_rows)

    return output_data

# Streamlit app starts here
st.title("NADAC Pricing Tool")

# Step 1: Upload Top 100 Spreadsheet
top_100_file = st.file_uploader("Upload Top 100 Spreadsheet (CSV)", type=["csv"])

# Step 2: Upload NADAC Spreadsheet
nadac_file = st.file_uploader("Upload NADAC Spreadsheet (CSV)", type=["csv"])

# Step 3: Upload Reimbursement Spreadsheet
reimbursement_file = st.file_uploader("Upload Reimbursement Spreadsheet (CSV)", type=["csv"])

# Process the files
if st.button("Process Data"):
    if not top_100_file or not nadac_file or not reimbursement_file:
        st.error("Please upload all three required files.")
    else:
        try:
            # Load the uploaded files as dataframes
            top_100_data = pd.read_csv(top_100_file)
            nadac_data = pd.read_csv(nadac_file)
            reimbursement_data = pd.read_csv(reimbursement_file)

            # Process the files
            output_data = process_files_with_adjusted_filtering(top_100_data, nadac_data, reimbursement_data)

            # Display the processed data
            st.write("Processed Data:")
            st.dataframe(output_data)

            # Provide a download button for the output CSV
            csv = output_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Output CSV",
                data=csv,
                file_name="processed_output.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"An error occurred: {e}")
