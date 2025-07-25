// --- Data injected from Python ---
let samples = window.q2_gunc_samples || {};
let summaryData = window.q2_gunc_summaryData || [];

// Create GUNC Summary Visualization
function createSummaryPlot(filteredData = null, reverseY = true, isFeatureDataMAG = false) {
  let dataToUse = filteredData || summaryData;
  // Apply taxonomic level filter
  const levelSelector = document.getElementById('level-selector');
  const selectedLevel = levelSelector ? levelSelector.value : 'species';
  dataToUse = dataToUse.filter(d => d.taxonomic_level === selectedLevel);
  // Apply GUNC pass filter if checkbox is checked
  const filterCheckbox = document.getElementById('filter-gunc-pass');
  if (filterCheckbox && ! filterCheckbox.checked) {
    // Handle both boolean and string representations of pass/fail
    dataToUse = dataToUse.filter(d => {
      const passValue = d.pass_gunc;
      return passValue === true || passValue === "True" || passValue === "true" || passValue === "Pass" || passValue === "pass";
    });
  }
  // Check if we have any data left
  if (dataToUse.length === 0) {
    console.warn('No data to plot after filtering');
    // Show empty plot or message
    const spec = {
      "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
      "description": "No data available",
      "width": 400,
      "height": 400,
      "data": {"values": []},
      "mark": {"type": "text", "text": "No data matches current filters", "fontSize": 18, "color": "#666"},
      "encoding": {
        "x": {"value": 200},
        "y": {"value": 200}
      }
    };
    vegaEmbed('#gunc-summary-plot', spec, {actions: false}).catch(console.error);
    return;
  }
  // Calculate dynamic axis limits
  // Filter out null/undefined/non-numeric values
  const refScores = dataToUse.map(d => Number(d.reference_representation_score)).filter(v => typeof v === 'number' && !isNaN(v));
  const contamLevels = dataToUse.map(d => Number(d.contamination_portion)).filter(v => typeof v === 'number' && !isNaN(v));
  let minRefScore = refScores.length > 0 ? Math.min(...refScores) : 0;
  let maxRefScore = refScores.length > 0 ? Math.max(...refScores) : 1;
  let maxContam = contamLevels.length > 0 ? Math.max(...contamLevels) : 1;
  // Smart axis limits with fallbacks
  let xMin = Math.max(0, minRefScore * 0.9).toFixed(2); // 0.9x min value, but not below 0
  let xMax = Math.min(1.1, maxRefScore * 1.1).toFixed(2); // 1.1x max value, but cap at 1.1
  let yMin = 0; // Always start contamination at 0
  let yMax = Math.min(1.1, maxContam * 1.1).toFixed(2); // 1.1x max contamination, but cap at 1.1
  // If ranges are invalid, set to defaults and warn
  if (!isFinite(xMin) || !isFinite(xMax) || xMin === xMax) {
    xMin = 0; xMax = 1;
  }
  if (!isFinite(yMin) || !isFinite(yMax) || yMin === yMax) {
    yMin = 0; yMax = 1;
  }
  // Update summary-card badge spans
  const sampleCountSpan = document.querySelector('.stat-value.text-info');
  const passCountSpan = document.querySelector('.stat-value.text-accent');
  const failCountSpan = document.querySelector('.stat-value.text-error');
  
  // For FeatureData[MAG], show "-" for sample count since samples are not meaningful
  const sampleCount = isFeatureDataMAG ? "-" : new Set(dataToUse.map(d => d.sample_id)).size;
  const passCount = dataToUse.filter(d => {
    const passValue = d.pass_gunc;
    return passValue === true || passValue === "True" || passValue === "true" || passValue === "Pass" || passValue === "pass";
  }).length;
  const failCount = dataToUse.length - passCount;
  if (sampleCountSpan) sampleCountSpan.textContent = sampleCount;
  if (passCountSpan) passCountSpan.textContent = passCount;
  if (failCountSpan) failCountSpan.textContent = failCount;
  // Normalize pass_gunc field to boolean for Vega-Lite
  const normalizedData = dataToUse.map(d => ({
    ...d,
    pass_gunc: d.pass_gunc === true || d.pass_gunc === "True" || d.pass_gunc === "true" || d.pass_gunc === "Pass" || d.pass_gunc === "pass"
  }));
  const spec = {
    "$schema": "https://vega.github.io/schema/vega-lite/v6.json",
    "description": "MAG Quality Summary from GUNC Analysis",
    "width": "container",
    "height": 500,
    "data": {
      "values": normalizedData
    },
    "params": [
      {
        "name": "grid",
        "select": "interval",
        "bind": "scales"
      },
      {
        "name": "ref_score_min",
        "value": xMin,
        "bind": {
          "input": "range",
          "min": xMin,
          "max": xMax,
          "step": 0.01,
          "name": "Min. reference score:"
        }
      },
      {
        "name": "contam_max",
        "value": yMax,
        "bind": {
          "input": "range",
          "min": yMin,
          "max": yMax,
          "step": 0.01,
          "name": "Max. contamination:"
        }
      }
    ],
    "config": {
      "legend": {
        "orient": "right",
        "titleFontSize": 13,
        "labelFontSize": 12,
        "columns": 3
      }
    },
    "transform": [
      {
        "filter": "datum.reference_representation_score >= ref_score_min"
      },
      {
        "filter": "datum.contamination_portion <= contam_max"
      }
    ],
    "mark": {
      "type": "point",
      "strokeWidth": 1.5
    },
    "encoding": {
      "x": {
        "field": "reference_representation_score",
        "type": "quantitative",
        "scale": {"domain": [xMin, xMax]},
        "title": "Reference Representation Score",
        "axis": {"grid": true, "gridOpacity": 0.6, "titleFontSize": 15, "labelFontSize": 13}
      },
      "y": {
        "field": "contamination_portion", 
        "type": "quantitative",
        "scale": {"domain": [yMin, yMax], "reverse": reverseY},
        "title": "Contamination Fraction",
        "axis": {"grid": true, "gridOpacity": 0.6, "titleFontSize": 15, "labelFontSize": 13}
      },
      "size": {
        "field": "n_contigs",
        "type": "quantitative",
        "scale": {"range": [100, 400]},
        "title": "Number of contigs"
      },
      "color": {
        "field": "sample_id",
        "type": "nominal",
        "scale": {"scheme": "viridis"},
        "title": "Sample ID"
      },
      "fill": {
        "field": "sample_id",
        "type": "nominal",
        "scale": {"scheme": "viridis"},
      },
      "fillOpacity": {
        "condition": {
          "test": "datum.pass_gunc",
          "value": 1
        },
        "value": 0
      },
      "tooltip": [
        {"field": "sample_id", "type": "nominal", "title": "Sample ID"},
        {"field": "mag_id", "type": "nominal", "title": "MAG ID"},
        {"field": "reference_representation_score", "type": "quantitative", "title": "Reference Rep. Score", "format": ".3f"},
        {"field": "contamination_portion", "type": "quantitative", "title": "Contamination", "format": ".3f"},
        {"field": "genes_retained_index", "type": "quantitative", "title": "Genes Retained Index", "format": ".3f"},
        {"field": "n_contigs", "type": "quantitative", "title": "Contigs"},
        {"field": "n_genes_mapped", "type": "quantitative", "title": "Genes Mapped"},
        {"field": "pass_gunc", "type": "nominal", "title": "GUNC Pass"}
      ]
    }
  };
  vegaEmbed('#gunc-summary-plot', spec, {
    actions: true
  }).then(result => {
    // Add custom styling to the sliders
    const container = document.getElementById('gunc-summary-plot');
    // Move the sliders container to the controls-container div
    const controlsContainer = document.getElementById('controls-container');
    const sliders = container.querySelector('.vega-bindings');
    if (controlsContainer && sliders) {
      // If a previous .vega-bindings exists in controlsContainer, remove it before appending the new one
      const oldBindings = controlsContainer.querySelector('.vega-bindings');
      if (oldBindings && oldBindings !== sliders) {
        oldBindings.remove();
      }
      controlsContainer.appendChild(sliders);
    }
  }).catch(console.error);
}

// Initialize dropdowns
document.addEventListener('DOMContentLoaded', function() {
  const sampleSelector = document.getElementById('sample-selector');
  const magSelector = document.getElementById('mag-selector');
  const plotCard = document.getElementById('plot-card');
  const plotContainer = document.getElementById('plot-container');
  const loadingSpinner = document.getElementById('loading-spinner');
  const reverseYAxisCheckbox = document.getElementById('reverse-y-axis');
  
  // Calculate this once and pass to functions that need it
  const sampleKeys = Object.keys(samples).sort();
  const isFeatureDataMAG = sampleKeys.includes("") && sampleKeys.length === 1;
  
  // Create the summary plot
  createSummaryPlot(null, reverseYAxisCheckbox ? reverseYAxisCheckbox.checked : true, isFeatureDataMAG);
  // Add event listener for GUNC pass filter checkbox
  const filterCheckbox = document.getElementById('filter-gunc-pass');
  if (filterCheckbox) {
    filterCheckbox.addEventListener('change', updatePlot);
  }
  // Add event listener for taxonomic level selector
  const levelSelector = document.getElementById('level-selector');
  if (levelSelector) {
    levelSelector.addEventListener('change', updatePlot);
  }
  // Add event listener for Y-axis reversal checkbox
  if (reverseYAxisCheckbox) {
    reverseYAxisCheckbox.addEventListener('change', updatePlot);
  }
  // Function to update plot based on current selections
  function updatePlot() {
    const selectedSample = sampleSelector.value;
    const reverseY = reverseYAxisCheckbox ? reverseYAxisCheckbox.checked : true;
    if (selectedSample === "") {
      createSummaryPlot(null, reverseY, isFeatureDataMAG);
    } else {
      const filteredData = summaryData.filter(item => item.sample_id === selectedSample);
      createSummaryPlot(filteredData, reverseY, isFeatureDataMAG);
    }
  }
  // Populate sample dropdown with "All Samples" option first
  sampleKeys.forEach(sampleId => {
    const option = document.createElement('option');
    option.value = sampleId;
    // Handle empty string keys with a more descriptive label
    option.textContent = sampleId === "" ? "(Default)" : sampleId;
    sampleSelector.appendChild(option);
  });
  
  // For FeatureData[MAG], disable sample selector and enable MAG selector
  // For SampleData[MAGs], default to showing all samples
  if (isFeatureDataMAG) {
    sampleSelector.value = "";
    sampleSelector.disabled = true;
    magSelector.disabled = false;
    // Populate MAGs immediately for FeatureData[MAG]
    populateMAGs("", isFeatureDataMAG);
  } else {
    sampleSelector.value = "";
    sampleSelector.disabled = false;
    magSelector.disabled = true;
  }
  // Function to populate MAG dropdown
  function populateMAGs(selectedSample, isFeatureDataMAG) {
    magSelector.innerHTML = '<option value="">-- Select a MAG --</option>';
    plotCard.style.display = 'none';
    
    // For FeatureData[MAG], selectedSample should be "" and MAGs should be available
    if (isFeatureDataMAG && selectedSample === "") {
      magSelector.disabled = false;
      const magIds = samples[""].slice().sort();
      magIds.forEach(magId => {
        const option = document.createElement('option');
        option.value = magId;
        option.textContent = magId;
        magSelector.appendChild(option);
      });
      // Preselect first MAG if available
      if (magIds.length > 0) {
        magSelector.value = magIds[0];
        // Automatically load the plot for the first MAG
        loadPlot(selectedSample, magIds[0], isFeatureDataMAG);
      }
      return;
    }
    
    // Handle "All Samples" selection for SampleData[MAGs] (empty value = all samples)
    if (selectedSample === "" || selectedSample === null || selectedSample === undefined) {
      magSelector.disabled = true;
      return;
    }
    
    // Check if selectedSample exists as a key in samples (including empty string)
    const hasValidSample = samples.hasOwnProperty(selectedSample);
    magSelector.disabled = !hasValidSample;
    if (hasValidSample && samples[selectedSample]) {
      const magIds = samples[selectedSample].slice().sort();
      magIds.forEach(magId => {
        const option = document.createElement('option');
        option.value = magId;
        option.textContent = magId;
        magSelector.appendChild(option);
      });
      // Preselect first MAG if available
      if (magIds.length > 0) {
        magSelector.value = magIds[0];
        // Automatically load the plot for the first MAG
        loadPlot(selectedSample, magIds[0], isFeatureDataMAG);
      }
    }
  }
  // Handle sample selection
  sampleSelector.addEventListener('change', function() {
    const selectedSample = this.value;
    // Update plot with new sample selection
    updatePlot();
    // Update MAG dropdown
    populateMAGs(selectedSample, isFeatureDataMAG);
  });
  // Handle MAG selection
  magSelector.addEventListener('change', function() {
    const selectedSample = sampleSelector.value;
    const selectedMag = this.value;
    // Check if we have valid selections (including empty string sample keys)
    const hasValidSample = selectedSample !== null && selectedSample !== undefined && samples.hasOwnProperty(selectedSample);
    const hasValidMag = selectedMag && selectedMag !== "";
    if (hasValidSample && hasValidMag) {
      loadPlot(selectedSample, selectedMag, isFeatureDataMAG);
    } else {
      plotCard.style.display = 'none';
    }
  });
  // Function to load plot HTML
  function loadPlot(sampleId, magId, isFeatureDataMAG) {
    // Construct plot URL based on input type
    const plotUrl = isFeatureDataMAG && sampleId === "" 
      ? `plots/${magId}.viz.html`  // FeatureData[MAG]: plots directly in plots/ folder
      : `plots/${sampleId}/${magId}.viz.html`;  // SampleData[MAGs]: plots in sample subfolder
      
    plotCard.style.display = 'block';
    loadingSpinner.style.display = 'block';
    plotContainer.innerHTML = '';
    fetch(plotUrl)
      .then(response => {
        if (!response.ok) {
          throw new Error(`Failed to load plot: ${response.status} ${response.statusText}`);
        }
        return response.text();
      })
      .then(html => {
        plotContainer.innerHTML = html;
        loadingSpinner.style.display = 'none';
        // Execute any scripts in the loaded HTML
        const scripts = plotContainer.querySelectorAll('script');
        scripts.forEach(script => {
          const newScript = document.createElement('script');
          newScript.textContent = script.textContent;
          if (script.src) {
            newScript.src = script.src;
          }
          document.head.appendChild(newScript);
        });
      })
      .catch(error => {
        console.error('Error loading plot:', error);
        plotContainer.innerHTML = `
          <div class="alert alert-warning" role="alert">
            <h6>Plot not available</h6>
            <p>Could not load plot for sample "${sampleId}" and MAG "${magId}".</p>
            <small class="text-muted">Expected location: ${plotUrl}</small>
          </div>
        `;
        loadingSpinner.style.display = 'none';
      });
  }
});
