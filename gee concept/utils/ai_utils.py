from groq import Groq


def get_ai_interpretation(index_name, stats_before, stats_after, context="heritage site"):
    # ---------------------------------------------------------------
    GROQ_API_KEY = "miaumiau"
    # ---------------------------------------------------------------

    client = Groq(api_key=GROQ_API_KEY)

    diff_mean = stats_after['mean'] - stats_before['mean']

    prompt = f"""You are an expert in satellite remote sensing and cultural heritage conservation.
Analyze the following change in the {index_name} index for a {context}:

- Value in Period 1: {stats_before['mean']:.4f}
- Value in Period 2: {stats_after['mean']:.4f}
- Absolute Change: {diff_mean:.4f}

Provide a concise professional interpretation (6-7 sentences) covering:
1. What this change physically represents (e.g., vegetation growth, urban encroachment, soil erosion).
2. Potential risks to the heritage site.
3. Recommended action for conservators.

Write in a clear, informative style suitable for heritage professionals.
Write bullet points if it helps clarity, but keep it concise.

Respond in English only."""


"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a remote sensing and heritage conservation expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.4,
        )


        # Verifică dacă există conținut în răspuns
        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content
        else:
            return "Ai could not generate an interpretation for this change. Please review the data and try again."

    except Exception as e:
        st.error(f"Error during AI interpretation: {str(e)}")
        return 0
"""


def _rule_based_interpretation(index_name, stats_before, stats_after, context):
    diff = stats_after['mean'] - stats_before['mean']
    abs_diff = abs(diff)
    direction = "increased" if diff > 0 else "decreased"
    magnitude = "significantly" if abs_diff > 0.1 else "slightly" if abs_diff > 0.03 else "minimally"

    interpretations = {
        'NDVI': {
            'increased': (
                f"The NDVI has {magnitude} {direction} by {abs_diff:.4f}, indicating vegetation growth "
                f"or recovery at {context}. While recovery can be positive, dense growth near structures "
                f"may cause root damage or moisture retention. Conservators should monitor plant proximity "
                f"to built elements and assess whether encroachment poses structural risks."
            ),
            'decreased': (
                f"The NDVI has {magnitude} {direction} by {abs_diff:.4f}, indicating vegetation loss or "
                f"stress at {context}. Reduced cover increases erosion risk and soil instability near "
                f"heritage structures. Conservators should assess the cause of decline and implement "
                f"erosion control measures promptly."
            ),
        },
        'NDBI': {
            'increased': (
                f"The NDBI has {magnitude} {direction} by {abs_diff:.4f}, suggesting increased built-up "
                f"area or urban encroachment near {context}. This may indicate new construction in the "
                f"buffer zone, increasing pollution and vibration risks. A ground survey and enforcement "
                f"of heritage protection zones is recommended."
            ),
            'decreased': (
                f"The NDBI has {magnitude} {direction} by {abs_diff:.4f}, indicating a reduction in "
                f"built-up surfaces near {context}. This could reflect demolition or surface rehabilitation. "
                f"Verify on-site to rule out unauthorized alterations and document current conditions."
            ),
        },
        'NDMI': {
            'increased': (
                f"The NDMI has {magnitude} {direction} by {abs_diff:.4f}, indicating higher moisture at "
                f"{context}. Elevated moisture accelerates biological growth on heritage structures and "
                f"increases freeze-thaw damage risk. Inspect drainage systems and apply preventive "
                f"biocide treatments if needed."
            ),
            'decreased': (
                f"The NDMI has {magnitude} {direction} by {abs_diff:.4f}, indicating drying conditions "
                f"at {context}. Reduced moisture may destabilize soils and increase erosion near "
                f"foundations. Monitor for cracking in earthen structures and manage irrigation accordingly."
            ),
        },
        'NDWI': {
            'increased': (
                f"The NDWI has {magnitude} {direction} by {abs_diff:.4f}, suggesting increased surface "
                f"water near {context}. Flooding or waterlogging poses serious risks to buried features "
                f"and foundations. Immediate drainage assessment and waterproofing inspection is advised."
            ),
            'decreased': (
                f"The NDWI has {magnitude} {direction} by {abs_diff:.4f}, indicating reduced surface "
                f"water near {context}. Persistent decline may affect groundwater and destabilize "
                f"moisture-sensitive materials. Monitor for differential settlement at the site."
            ),
        },
        'BSI': {
            'increased': (
                f"The BSI has {magnitude} {direction} by {abs_diff:.4f}, indicating increased bare soil "
                f"exposure at {context}. This heightens erosion risk and may uncover sensitive subsurface "
                f"deposits. Revegetation and erosion control measures should be prioritized immediately."
            ),
            'decreased': (
                f"The BSI has {magnitude} {direction} by {abs_diff:.4f}, indicating reduced bare soil "
                f"at {context}. Increased vegetation cover generally improves soil stability, but dense "
                f"growth should be monitored for root intrusion into buried structures."
            ),
        },
    }

    interp = interpretations.get(index_name, {})
    return interp.get(direction, (
        f"The {index_name} index has {magnitude} {direction} by {abs_diff:.4f} at {context}. "
        f"This warrants further investigation to determine physical cause and heritage impact. "
        f"A field assessment is recommended to correlate satellite observations with ground conditions."
    ))