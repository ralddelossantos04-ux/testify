// Philippine Address Data via PSGC API
// Maps hardcoded province names from the dropdowns to their corresponding PSGC codes.
const PH_PROV_MAP = {
    "Ilocos Norte": "012800000", "Ilocos Sur": "012900000", "La Union": "013300000", "Pangasinan": "015500000", 
    "Batanes": "020900000", "Cagayan": "021500000", "Isabela": "023100000", "Nueva Vizcaya": "025000000", 
    "Quirino": "025700000", "Bataan": "030800000", "Bulacan": "031400000", "Nueva Ecija": "034900000", 
    "Pampanga": "035400000", "Tarlac": "036900000", "Zambales": "037100000", "Aurora": "037700000", 
    "Batangas": "041000000", "Cavite": "042100000", "Laguna": "043400000", "Quezon": "045600000", 
    "Rizal": "045800000", "Marinduque": "174000000", "Occidental Mindoro": "175100000", "Oriental Mindoro": "175200000", 
    "Palawan": "175300000", "Romblon": "175900000", "Albay": "050500000", "Camarines Norte": "051600000", 
    "Camarines Sur": "051700000", "Catanduanes": "052000000", "Masbate": "054100000", "Sorsogon": "056200000", 
    "Aklan": "060400000", "Antique": "060600000", "Capiz": "061900000", "Iloilo": "063000000", 
    "Negros Occidental": "064500000", "Guimaras": "067900000", "Bohol": "071200000", "Cebu": "072200000", 
    "Negros Oriental": "074600000", "Siquijor": "076100000", "Eastern Samar": "082600000", "Leyte": "083700000", 
    "Northern Samar": "084800000", "Samar": "086000000", "Southern Leyte": "086400000", "Biliran": "087800000", 
    "Zamboanga Del Norte": "097200000", "Zamboanga Del Sur": "097300000", "Zamboanga Sibugay": "098300000", 
    "Bukidnon": "101300000", "Camiguin": "101800000", "Lanao Del Norte": "103500000", "Misamis Occidental": "104200000", 
    "Misamis Oriental": "104300000", "Davao Del Norte": "112300000", "Davao Del Sur": "112400000", 
    "Davao Oriental": "112500000", "Davao De Oro": "118200000", "Davao Occidental": "118600000", 
    "Cotabato": "124700000", "South Cotabato": "126300000", "Sultan Kudarat": "126500000", "Sarangani": "128000000", 
    "Abra": "140100000", "Benguet": "141100000", "Ifugao": "142700000", "Kalinga": "143200000", 
    "Mountain Province": "144400000", "Apayao": "148100000", "Agusan Del Norte": "160200000", "Agusan Del Sur": "160300000", 
    "Surigao Del Norte": "166700000", "Surigao Del Sur": "166800000", "Dinagat Islands": "168500000", 
    "Basilan": "150700000", "Lanao Del Sur": "153600000", "Maguindanao": "153800000", "Sulu": "156600000", 
    "Tawi-Tawi": "157000000", "Metro Manila": "130000000",
    
    // Add aliases for potential mismatch
    "Zamboanga del Norte": "097200000", "Zamboanga del Sur": "097300000", 
    "Agusan del Norte": "160200000", "Agusan del Sur": "160300000", 
    "Surigao del Norte": "166700000", "Surigao del Sur": "166800000",
    "Lanao del Norte": "103500000", "Lanao del Sur": "153600000",
    "Davao del Norte": "112300000", "Davao del Sur": "112400000",
    "Maguindanao del Norte": "153800000", "Maguindanao del Sur": "153800000" // Grouped temporarily as Maguindanao
};

function populateMunicipalities(provinceName, munSelectElem, barSelectElem) {
    if (!munSelectElem) return;
    
    munSelectElem.innerHTML = '<option value="">Loading...</option>';
    if (barSelectElem) {
        barSelectElem.innerHTML = '<option value="">— Barangay —</option>';
    }

    const code = PH_PROV_MAP[provinceName] || PH_PROV_MAP[titleCase(provinceName)];
    
    if (!code) {
        munSelectElem.innerHTML = '<option value="">— Municipality —</option>';
        return;
    }

    // Metro Manila uses region endpoint
    const url = code === "130000000" 
        ? `https://psgc.gitlab.io/api/regions/${code}/cities-municipalities/`
        : `https://psgc.gitlab.io/api/provinces/${code}/cities-municipalities/`;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            munSelectElem.innerHTML = '<option value="">— Municipality —</option>';
            // Sort by name
            data.sort((a, b) => a.name.localeCompare(b.name));
            
            data.forEach(item => {
                const option = document.createElement('option');
                option.value = item.name;
                // Store PSGC code for barangay fetching
                option.dataset.code = item.code;
                option.textContent = item.name;
                munSelectElem.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error fetching municipalities:', error);
            munSelectElem.innerHTML = '<option value="">— Municipality —</option>';
            
            // Fallback
            const fb = document.createElement('option');
            fb.value = "N/A";
            fb.textContent = "Error loading data";
            munSelectElem.appendChild(fb);
        });
}

function populateBarangays(provinceName, municipalityName, barSelectElem) {
    if (!barSelectElem) return;
    
    barSelectElem.innerHTML = '<option value="">Loading...</option>';

    // Find the correct municipality element and its data-code
    // Note: Because populateBarangays is called from onChange, we must grab the selected option
    // Since we don't pass the select element directly, we search the DOM or we can query it
    
    // In students.html & teachers.html, we pass the *value*, so let's find the active option
    const activeMunOption = document.querySelector(`select option[value="${municipalityName}"]:checked`);
    
    if (!activeMunOption || !activeMunOption.dataset.code) {
        barSelectElem.innerHTML = '<option value="">— Barangay —</option>';
        return;
    }

    const munCode = activeMunOption.dataset.code;

    fetch(`https://psgc.gitlab.io/api/cities-municipalities/${munCode}/barangays/`)
        .then(response => response.json())
        .then(data => {
            barSelectElem.innerHTML = '<option value="">— Barangay —</option>';
            data.sort((a, b) => a.name.localeCompare(b.name));
            
            data.forEach(item => {
                const option = document.createElement('option');
                option.value = item.name;
                option.textContent = item.name;
                barSelectElem.appendChild(option);
            });
            
            if(data.length === 0) {
                const option = document.createElement('option');
                option.value = municipalityName; // Fallback to municipality name
                option.textContent = "No Barangays available";
                barSelectElem.appendChild(option);
            }
        })
        .catch(error => {
            console.error('Error fetching barangays:', error);
            barSelectElem.innerHTML = '<option value="">— Barangay —</option>';
            
            // Fallback
            const fb = document.createElement('option');
            fb.value = "N/A";
            fb.textContent = "Error loading data";
            barSelectElem.appendChild(fb);
        });
}

function resetAddressDropdowns(munSelectId, barSelectId) {
    const munSelectElem = document.getElementById(munSelectId);
    const barSelectElem = document.getElementById(barSelectId);
    
    if (munSelectElem) {
        munSelectElem.innerHTML = '<option value="">— Municipality —</option>';
    }
    if (barSelectElem) {
        barSelectElem.innerHTML = '<option value="">— Barangay —</option>';
    }
}

function titleCase(str) {
    if(!str) return "";
    return str.toLowerCase().split(' ').map(word => {
        return word.replace(word[0], word[0].toUpperCase());
    }).join(' ');
}
