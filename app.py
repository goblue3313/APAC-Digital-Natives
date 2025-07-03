import streamlit as st
import pandas as pd
from openai import OpenAI
from urllib.parse import urlparse
import time
import json
import os
from dotenv import load_dotenv
import numpy as np

# Load environment variables
load_dotenv()

# Configure OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def load_excel_data():
    """Load and return the Excel data"""
    try:
        df = pd.read_excel('data.xlsx')
        return df
    except FileNotFoundError:
        st.error("Error: data.xlsx file not found!")
        return None
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

def safe_convert_to_int(value, default=0):
    """Safely convert a value to integer, handling NaN and string cases"""
    try:
        # Handle NaN values
        if pd.isna(value) or value is None:
            return default
        
        # Handle string values
        if isinstance(value, str):
            # Remove commas and strip whitespace
            value = value.replace(',', '').strip()
            # Handle empty strings
            if value == '' or value.lower() == 'nan':
                return default
        
        # Convert to float first, then to int
        return int(float(value))
    except (ValueError, TypeError):
        return default

def search_company_data(df, company_name):
    """Search for company match in Excel data, try exact match first, then fuzzy match"""
    # Try exact match first
    exact_result = df[df['Organization Name'].str.lower() == company_name.lower()]
    
    if not exact_result.empty:
        # Get the first exact match
        row = exact_result.iloc[0]
        
        # Handle number formatting with safe conversion
        visits = safe_convert_to_int(row['Monthly Website Visits'], 0)
        downloads = safe_convert_to_int(row['App Downloads Last 30 Days'], 0)
        
        return {
            'company_name': row['Organization Name'],
            'website': row['Website'] if pd.notna(row['Website']) else f"https://www.{company_name.lower().replace(' ', '')}.com",
            'monthly_visits': visits,
            'app_downloads': downloads,
            'match_type': 'exact'
        }
    
    # If no exact match, try partial match
    partial_result = df[df['Organization Name'].str.lower().str.contains(company_name.lower(), na=False)]
    
    if not partial_result.empty:
        # Get the first partial match
        row = partial_result.iloc[0]
        
        # Handle number formatting with safe conversion
        visits = safe_convert_to_int(row['Monthly Website Visits'], 0)
        downloads = safe_convert_to_int(row['App Downloads Last 30 Days'], 0)
        
        return {
            'company_name': row['Organization Name'],
            'website': row['Website'] if pd.notna(row['Website']) else f"https://www.{company_name.lower().replace(' ', '')}.com",
            'monthly_visits': visits,
            'app_downloads': downloads,
            'match_type': 'partial'
        }
    
    # If no match found, return default data structure with the user input
    return {
        'company_name': company_name,
        'website': f"https://www.{company_name.lower().replace(' ', '')}.com",
        'monthly_visits': 0,
        'app_downloads': 0,
        'match_type': 'none'
    }

def extract_domain(url):
    """Extract domain from URL"""
    try:
        if pd.isna(url) or url is None:
            return "Unknown"
        parsed = urlparse(str(url))
        return parsed.netloc.replace('www.', '') if parsed.netloc else str(url)
    except:
        return str(url) if url else "Unknown"

def create_comprehensive_prep_prompt(company_data):
    """Create the comprehensive preparation sheet prompt used for both stages"""
    
    company_domain = extract_domain(company_data['website'])
    
    # Adjust prompt based on whether we have real data or not
    if company_data['match_type'] == 'none':
        data_note = f"""
**Note:** No internal data available for this company. Please research and find accurate traffic and app download data during your analysis.

**Research Target:**
- Company: {company_data['company_name']}
- Estimated Website: {company_data['website']} (please verify correct URL)
"""
    else:
        match_note = "✅ Exact match" if company_data['match_type'] == 'exact' else "📍 Partial match"
        visits_display = f"{company_data['monthly_visits']:,}" if company_data['monthly_visits'] > 0 else "Data not available"
        downloads_display = f"{company_data['app_downloads']:,}" if company_data['app_downloads'] > 0 else "Data not available"
        
        data_note = f"""
**Verified Internal Data ({match_note}):**
- Monthly Website Visits: {visits_display}
- App Downloads (Last 30 Days): {downloads_display}
"""
    
    return f"""You are an expert AI sales research analyst. Generate a comprehensive executive preparation sheet for OpenAI API sales prospects.

## Research Requirements:
1. **Company Intelligence**: Search for company background, size, headquarters, key markets
2. **Technology Analysis**: Identify tech stack, cloud providers, AI/ML tools currently used
3. **Funding & Growth**: Find latest funding rounds, valuation, growth metrics, investor information
4. **AI Readiness**: Look for AI initiatives, job postings mentioning AI/ML, existing AI products
5. **Digital Presence**: Research traffic data and app performance metrics
6. **Competitive Position**: Research market position and key competitors

## Output Format (use exactly this structure):
# 📄 Prep Sheet – {company_data['company_name']}

## 1. Fast Facts
- **HQ / Key APAC markets:** [location and key markets]
- **Employees / Engineers:** [headcount with engineering team size if available]
- **Funding:** [latest round, date, total raised, key investors]
- **Digital Footprint:** [monthly visits] monthly visits / [app downloads] app downloads{' (verified from internal data)' if company_data['match_type'] != 'none' else ' (researched data)'}

## 2. Tech Stack (BuiltWith)  
| Layer | Detected Tools |
|-------|----------------|
| Cloud | [AWS/GCP/Azure and specific services] |
| Backend | [programming languages, frameworks, databases] |
| AI / Analytics | [OpenAI, TensorFlow, analytics tools, etc.] |

## 3. AI-Readiness Signals
- [Signal 1: existing AI initiatives, products, or features]
- [Signal 2: AI-related job postings or team growth]
- [Signal 3: technology partnerships or integrations]
- [Signal 4: public statements about AI strategy]

## 4. Potential OpenAI API Use Cases
1. **[Use Case 1]**: [Specific application based on their business model]
2. **[Use Case 2]**: [Customer-facing or internal efficiency opportunity]
3. **[Use Case 3]**: [Innovation or competitive advantage opportunity]

## 5. Discovery Questions
- "[Question about their current AI initiatives or challenges]"
- "[Question about specific use case identified above]"
- "[Question about technical implementation or integration needs]"

**Fit Score:** [0-100] / 100 → *[High/Medium/Low] propensity*

## Scoring Methodology:
- +25 points: Series B+ funding OR $25M+ total raised
- +20 points: 1M+ monthly active users (web + app)
- +20 points: Existing AI/ML tools in tech stack
- +15 points: 5+ AI-related job openings
- +10 points: Recent AI product launches or announcements
- +10 points: Enterprise cloud infrastructure (AWS/GCP/Azure)

## Research Quality Standards:
- Use BuiltWith, Crunchbase, SimilarWeb, company websites, and reputable tech press
- Include inline citations with `` format
- Prioritize recent data (last 12 months)
- Be specific with numbers, dates, and sources
- If data unavailable, state "Data not found" rather than speculate

**Company:** {company_data['company_name']}
**Website:** {company_data['website']}
**Domain:** {company_domain}

{data_note}

Research this company thoroughly using web search and generate a detailed preparation sheet. Focus on their technology stack, AI readiness, funding status, and potential OpenAI API use cases."""

def stage1_gpt4o_prep_sheet(company_data, progress_placeholder, status_placeholder):
    """Stage 1: Use GPT-4o with web search to create complete prep sheet"""
    
    prep_prompt = create_comprehensive_prep_prompt(company_data)
    
    input_text = f"Conduct comprehensive research on {company_data['company_name']} and generate a detailed preparation sheet using web search."

    try:
        progress_placeholder.progress(0.3)
        status_placeholder.info("🔍 Step 1: GPT-4o creating prep sheet with web search...")
        
        # Stage 1: Complete prep sheet with GPT-4o + web search
        response = client.responses.create(
            model="gpt-4o",
            instructions=prep_prompt,
            input=input_text,
            tools=[
                {"type": "web_search"}
            ]
        )
        
        progress_placeholder.progress(0.6)
        status_placeholder.success("✅ Step 1: GPT-4o prep sheet completed!")
        
        # Extract the prep sheet
        if hasattr(response, 'output') and response.output:
            for item in response.output:
                if hasattr(item, 'type') and item.type == 'message':
                    if hasattr(item, 'content') and item.content:
                        for content_item in item.content:
                            if hasattr(content_item, 'type') and content_item.type == 'output_text':
                                return content_item.text
        
        return str(response.output_text) if hasattr(response, 'output_text') else str(response)
        
    except Exception as e:
        progress_placeholder.progress(0.6)
        status_placeholder.error(f"❌ Step 1 failed: {str(e)}")
        return f"GPT-4o prep sheet generation failed: {str(e)}"

def stage2_o1_enhancement(company_data, gpt4o_prep_sheet, progress_placeholder, status_placeholder):
    """Stage 2: Use o1-preview to enhance and refine the GPT-4o prep sheet"""
    
    company_domain = extract_domain(company_data['website'])
    
    # Stage 2: Enhancement prompt for o1-preview
    enhancement_prompt = f"""You are an expert AI sales strategist and analyst. You have been provided with a comprehensive preparation sheet created by GPT-4o with web search. Your task is to enhance, refine, and improve this prep sheet using your advanced reasoning capabilities.

**ENHANCEMENT OBJECTIVES:**
1. **Analytical Depth**: Add deeper strategic insights and analysis
2. **Data Synthesis**: Better synthesize the information for executive consumption
3. **Strategic Recommendations**: Enhance the OpenAI API use cases with more sophisticated reasoning
4. **Gap Filling**: Fill any missing information using your knowledge base
5. **Executive Polish**: Make the content more executive-ready and actionable

**ORIGINAL COMPANY DATA:**
- Company: {company_data['company_name']}
- Website: {company_data['website']}
- Data Match Type: {company_data['match_type']}
- Monthly Website Visits: {company_data['monthly_visits']:,}
- App Downloads (Last 30 Days): {company_data['app_downloads']:,}

**GPT-4O PREP SHEET TO ENHANCE:**
{gpt4o_prep_sheet}

**ENHANCEMENT INSTRUCTIONS:**
1. **Keep the same format structure** - don't change the overall layout
2. **Improve the analysis quality** - add deeper insights where possible
3. **Enhance strategic recommendations** - make OpenAI API use cases more compelling
4. **Fill knowledge gaps** - if GPT-4o missed something you know, add it
5. **Improve scoring rationale** - provide more detailed fit score reasoning
6. **Add executive insights** - include strategic implications and business impact
7. **Enhance discovery questions** - make them more targeted and valuable
8. **Preserve source links** - keep all the web search citations from GPT-4o

**SPECIFIC IMPROVEMENTS TO MAKE:**
- **Strategic Context**: Add broader market context and competitive implications
- **Technical Assessment**: Deeper analysis of their technical readiness for AI integration
- **Business Impact**: More specific ROI and business value propositions
- **Implementation Roadmap**: Suggestions for how they might approach OpenAI API adoption
- **Risk Assessment**: Potential challenges or considerations for their AI journey
- **Executive Summary**: Add a compelling executive summary at the end

**OUTPUT FORMAT:**
Enhance the existing prep sheet while maintaining the same structure. Add an enhanced executive summary section at the end:

[Enhanced version of the original prep sheet with your improvements]

## 8. Executive Summary & Strategic Implications
**Strategic Context:** [Market positioning and competitive landscape insights]
**Technical Readiness:** [Assessment of their ability to implement OpenAI API]
**Business Impact Potential:** [Quantified value propositions where possible]
**Recommended Implementation Approach:** [Suggested roadmap for OpenAI API adoption]
**Key Success Factors:** [Critical elements for successful implementation]
**Potential Challenges:** [Risks or obstacles to consider]

**Bottom Line:** [One compelling sentence on why this is a high/medium/low priority prospect]

**QUALITY STANDARDS:**
- Maintain all factual accuracy from the original
- Preserve web search citations and source links
- Add value through deeper analysis, not just rewording
- Focus on actionable insights for sales conversations
- Use your reasoning capabilities to provide strategic depth
- Keep the executive tone professional and compelling"""

    try:
        progress_placeholder.progress(0.8)
        status_placeholder.info("🧠 Step 2: o1-preview enhancing and refining prep sheet...")
        
        # Stage 2: Enhancement with o1-preview
        response = client.chat.completions.create(
            model="o1-preview",
            messages=[
                {
                    "role": "user", 
                    "content": enhancement_prompt
                }
            ]
        )
        
        progress_placeholder.progress(1.0)
        status_placeholder.success("✅ Step 2: o1-preview enhancement completed!")
        
        return response.choices[0].message.content
        
    except Exception as e:
        progress_placeholder.progress(1.0)
        status_placeholder.error(f"❌ Step 2 failed: {str(e)}")
        return f"o1-preview enhancement failed: {str(e)}\n\nOriginal GPT-4o prep sheet:\n{gpt4o_prep_sheet}"

def generate_enhanced_two_stage_prep_sheet(company_data, progress_placeholder, status_placeholder):
    """Orchestrate the enhanced two-stage process"""
    
    try:
        # Stage 1: GPT-4o Complete Prep Sheet
        progress_placeholder.progress(0.1)
        status_placeholder.info("🚀 Starting two-step process...")
        
        gpt4o_prep_sheet = stage1_gpt4o_prep_sheet(company_data, progress_placeholder, status_placeholder)
        
        if gpt4o_prep_sheet.startswith("GPT-4o prep sheet generation failed"):
            return gpt4o_prep_sheet
        
        # Brief pause between stages
        time.sleep(1)
        
        # Stage 2: o1-preview Enhancement
        enhanced_prep_sheet = stage2_o1_enhancement(company_data, gpt4o_prep_sheet, progress_placeholder, status_placeholder)
        
        return enhanced_prep_sheet
        
    except Exception as e:
        progress_placeholder.empty()
        status_placeholder.error(f"❌ Two-step process failed: {str(e)}")
        return f"Error in process: {str(e)}"

def main():
    st.set_page_config(
        page_title="APAC Digital Natives Prep-Sheet Generator", 
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 APAC Digital Natives Prep-Sheet Generator")
    st.markdown("*Use the box below to insert a Digital Native company in APAC to return a helpful pre-discovery sheet with key insights about the company. Please be patient as responses typically take 1-2 minutes to generate.*")
    st.markdown("---")
    
    # Process explanation in sidebar
    with st.sidebar:
        st.markdown("### Process Overview")
        st.info("""
        **Step 1: Complete Prep Sheet**
        🔍 GPT-4o takes comprehensive prompt
        📊 Web searches + completes analysis
        🔗 Real source links included
        📋 Full prep sheet generated
        
        **Step 2: Strategic Enhancement**
        🧠 o1-preview adds strategic depth
        💡 Enhanced insights & analysis
        🎯 Better use case recommendations
        📈 Executive-level polish
        """)
        
        st.markdown("### Why this approach?")
        st.success("""
        ✅ **Why this approach?**
        - GPT-4o: Excellent web research + concise output
        - o1-preview: Strategic depth + reasoning
        - Maintains GPT-4o's quality baseline
        - Adds o1's analytical sophistication
        """)
    
    # Load Excel data
    df = load_excel_data()
    if df is None:
        st.stop()
    
    # Input section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        company_input = st.text_input(
            "Enter Company Name:",
            placeholder="e.g., Canva, Shein, Tokopedia"
        )
    
    with col2:
        search_button = st.button("🔍 Generate Report", type="primary")
    
    if search_button and company_input:
        with st.spinner("Searching company data..."):
            # Search in Excel
            company_data = search_company_data(df, company_input)
            
            # Display found data with appropriate messaging
            if company_data['match_type'] == 'exact':
                st.success(f"✅ Exact match found: {company_data['company_name']}")
            elif company_data['match_type'] == 'partial':
                st.warning(f"📍 Partial match found: {company_data['company_name']}")
            else:
                st.info(f"🔍 No database match - will research: {company_data['company_name']}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if company_data['match_type'] != 'none' and company_data['monthly_visits'] > 0:
                    st.metric("Monthly Visits", f"{company_data['monthly_visits']:,}")
                else:
                    st.metric("Monthly Visits", "Will research")
            with col2:
                if company_data['match_type'] != 'none' and company_data['app_downloads'] > 0:
                    st.metric("App Downloads", f"{company_data['app_downloads']:,}")
                else:
                    st.metric("App Downloads", "Will research")
            with col3:
                st.metric("Website", extract_domain(company_data['website']))
            
            st.markdown("---")
            
            # Create progress indicators
            st.markdown("## 🔄 Two-Step Process")
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            # Add process info
            st.info("⏱️ **Process:** GPT-4o comprehensive prep sheet (45s) → o1-preview strategic enhancement (60s)")
            
            # Generate enhanced prep sheet
            enhanced_prep_sheet = generate_enhanced_two_stage_prep_sheet(
                company_data, 
                progress_placeholder, 
                status_placeholder
            )
            
            # Clear progress indicators
            time.sleep(1)
            progress_placeholder.empty()
            status_placeholder.empty()
            
            # Display results
            if enhanced_prep_sheet and not any(fail_text in enhanced_prep_sheet for fail_text in ["failed", "Error"]):
                st.markdown("## 📄 Pre-Discovery Company Research Sheet")
                st.success("🎉 Two-step research complete! GPT-4o quality + o1-preview insights:")
                st.markdown(enhanced_prep_sheet)
                
                # Copy button
                with st.expander("📋 Copy Markdown for Slack/Notion"):
                    st.code(enhanced_prep_sheet, language="markdown")
                
                # Download option
                st.download_button(
                    label="💾 Download Research Sheet",
                    data=enhanced_prep_sheet,
                    file_name=f"{company_data['company_name']}_pre_discovery.md", 
                    mime="text/markdown"
                )
            else:
                st.error("❌ Research process failed")
                if enhanced_prep_sheet:
                    st.code(enhanced_prep_sheet)
                
    # Sidebar with additional info
    with st.sidebar:
        st.markdown("### Key Features")
        st.info("""
        🌐 **GPT-4o web research quality**
        🧠 **o1-preview strategic insights**
        🔗 **Real source links preserved**
        💡 **Enhanced use case analysis**
        📊 **Executive-ready format**
        ⚡ **Efficient two-step process**
        """)
        
        st.markdown("### Database Stats")
        if df is not None:
            st.metric("Total Companies", len(df))
            st.metric("Data Source", "data.xlsx")
            st.info("💡 **Smart Matching:** Exact → Partial → Research any company")

if __name__ == "__main__":
    main()
