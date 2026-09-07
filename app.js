(() => {
  const cfg = window.ULPIN_CONFIG || {};
  const form = document.getElementById("propertyForm");
  const fileInput = document.getElementById("blueprint");
  const dropzone = document.getElementById("dropzone");
  const browseBtn = document.getElementById("browseBtn");
  const filePreview = document.getElementById("filePreview");
  const submitBtn = document.getElementById("submitBtn");
  const resultSection = document.getElementById("resultSection");
  const message = document.getElementById("message");
  const languageSelect = document.getElementById("languageSelect");
  const STORAGE = "ulpin_frontend_state_v5";
  const LANG = "ulpin_frontend_language_v5";
  let selectedFile = null;

  const translations = {
    en: {
      navRegistration:"Property Registration",navRecords:"3D Property Records",navHelp:"Help & Guidelines",
      propertySubmission:"Property submission",submissionIntro:"Enter information exactly as available in the land/property record.",
      existingLand:"Existing land identity",existingLandHelp:"The parent parcel's existing 2D identifier.",
      propertyDetails:"Property details",propertyDetailsHelp:"Basic details used to identify the property.",
      blueprint:"Blueprint / building plan",blueprintHelp:"Upload the available plan for processing and 3D model generation.",
      submit:"Submit for 3D processing",clear:"Clear form",copy:"Copy",copied:"Copied",
      warning:"Warning",ok:"OK",newSubmission:"Create another submission",saved:"Your entered details are saved in this browser.",
      noBlueprint:"Please choose a blueprint before submitting.",invalidFile:"This file type is not supported.",
      tooLarge:"The blueprint must be 25 MB or smaller.",missingBackend:"Backend URL is not configured. Update SUBMIT_URL in config.js.",
      submitFailed:"The submission could not be completed.",success:"Property submitted successfully.",
      confirm:"I confirm that the information provided corresponds to the submitted property record and blueprint."
    },
    hi:{navRegistration:"संपत्ति पंजीकरण",navRecords:"3D संपत्ति रिकॉर्ड",navHelp:"सहायता और दिशानिर्देश",propertySubmission:"संपत्ति जमा करें",submissionIntro:"भूमि/संपत्ति रिकॉर्ड के अनुसार जानकारी दर्ज करें।",existingLand:"मौजूदा भूमि पहचान",existingLandHelp:"मूल 2D भूमि पहचान दर्ज करें।",propertyDetails:"संपत्ति विवरण",propertyDetailsHelp:"संपत्ति की मूल जानकारी दें।",blueprint:"ब्लूप्रिंट / भवन योजना",blueprintHelp:"प्रसंस्करण के लिए भवन योजना अपलोड करें।",submit:"3D प्रसंस्करण के लिए जमा करें",clear:"फ़ॉर्म साफ़ करें",copy:"कॉपी",copied:"कॉपी किया गया",warning:"चेतावनी",ok:"ठीक है",newSubmission:"नई प्रविष्टि",saved:"आपकी जानकारी इस ब्राउज़र में सुरक्षित है।",noBlueprint:"जमा करने से पहले ब्लूप्रिंट चुनें।",invalidFile:"यह फ़ाइल प्रकार समर्थित नहीं है।",tooLarge:"ब्लूप्रिंट 25 MB या उससे कम होना चाहिए।",missingBackend:"बैकएंड URL कॉन्फ़िगर नहीं है। config.js में SUBMIT_URL अपडेट करें।",submitFailed:"सबमिशन पूरा नहीं हो सका।",success:"संपत्ति सफलतापूर्वक जमा हुई।",confirm:"मैं पुष्टि करता/करती हूँ कि दी गई जानकारी संपत्ति रिकॉर्ड और ब्लूप्रिंट से संबंधित है।"},
    te:{navRegistration:"ఆస్తి నమోదు",navRecords:"3D ఆస్తి రికార్డులు",navHelp:"సహాయం & మార్గదర్శకాలు",propertySubmission:"ఆస్తి సమర్పణ",submissionIntro:"భూమి/ఆస్తి రికార్డులో ఉన్నట్లుగా సమాచారం నమోదు చేయండి.",existingLand:"ప్రస్తుత భూమి గుర్తింపు",existingLandHelp:"మాతృ 2D భూమి గుర్తింపును నమోదు చేయండి.",propertyDetails:"ఆస్తి వివరాలు",propertyDetailsHelp:"ఆస్తి ప్రాథమిక సమాచారాన్ని ఇవ్వండి.",blueprint:"బ్లూప్రింట్ / భవన ప్రణాళిక",blueprintHelp:"ప్రాసెసింగ్ కోసం భవన ప్రణాళికను అప్‌లోడ్ చేయండి.",submit:"3D ప్రాసెసింగ్‌కు సమర్పించండి",clear:"ఫారమ్ క్లియర్ చేయండి",copy:"కాపీ",copied:"కాపీ అయింది",warning:"హెచ్చరిక",ok:"సరే",newSubmission:"మరో సమర్పణ",saved:"మీ సమాచారం ఈ బ్రౌజర్‌లో భద్రపరచబడింది.",noBlueprint:"సమర్పించే ముందు బ్లూప్రింట్ ఎంచుకోండి.",invalidFile:"ఈ ఫైల్ రకం మద్దతు లేదు.",tooLarge:"బ్లూప్రింట్ 25 MB లేదా అంతకంటే తక్కువగా ఉండాలి.",missingBackend:"బ్యాక్‌ఎండ్ URL కాన్ఫిగర్ కాలేదు. config.js లో SUBMIT_URL మార్చండి.",submitFailed:"సమర్పణ పూర్తి కాలేదు.",success:"ఆస్తి విజయవంతంగా సమర్పించబడింది.",confirm:"ఇచ్చిన సమాచారం ఆస్తి రికార్డు మరియు బ్లూప్రింట్‌కు సరిపోతుందని నేను నిర్ధారిస్తున్నాను."}
  };
  const shortLanguages = ["ta","bn","mr","gu","kn","ml","or","pa","as","ur"];
  shortLanguages.forEach(code => {
    translations[code] = {...translations.en};
  });

  function t(key){ return (translations[languageSelect.value] || translations.en)[key] || translations.en[key] || key; }

  function applyLanguage(code){
    languageSelect.value = code;
    localStorage.setItem(LANG, code);
    document.documentElement.lang = code;
    document.querySelectorAll(".nav-link").forEach((el,i)=>el.textContent=[t("navRegistration"),t("navRecords"),t("navHelp")][i]);
    const map = {
      propertySubmission:"h2", submissionIntro:"card-header p", existingLand:"", existingLandHelp:"",
      propertyDetails:"", propertyDetailsHelp:"", blueprint:"", blueprintHelp:""
    };
    const h2 = document.querySelector(".card-header h2"); if(h2) h2.textContent=t("propertySubmission");
    const intro = document.querySelector(".card-header p"); if(intro) intro.textContent=t("submissionIntro");
    const blocks=document.querySelectorAll(".block-heading");
    if(blocks[0]){blocks[0].querySelector("h3").textContent=t("existingLand");blocks[0].querySelector("p").textContent=t("existingLandHelp")}
    if(blocks[1]){blocks[1].querySelector("h3").textContent=t("propertyDetails");blocks[1].querySelector("p").textContent=t("propertyDetailsHelp")}
    if(blocks[2]){blocks[2].querySelector("h3").textContent=t("blueprint");blocks[2].querySelector("p").textContent=t("blueprintHelp")}
    document.querySelector(".primary-button[type=submit] span").textContent=t("submit");
    document.getElementById("resetBtn").textContent=t("clear");
    document.getElementById("newSubmission").textContent=t("newSubmission");
    document.querySelector(".consent span").textContent=t("confirm");
    document.getElementById("modalTitle")?.textContent;
    if(selectedFile) renderFile(selectedFile);
  }

  function modal(id, text=""){
    if(id==="errorModal") document.getElementById("modalText").textContent=text;
    document.getElementById(id).classList.remove("hidden");
  }
  function closeModal(id){document.getElementById(id).classList.add("hidden")}
  document.querySelectorAll("[data-close]").forEach(el=>el.addEventListener("click",()=>closeModal(el.dataset.close)));
  document.getElementById("modalClose").addEventListener("click",()=>closeModal("errorModal"));
  document.addEventListener("keydown",e=>{if(e.key==="Escape"){closeModal("errorModal");closeModal("helpModal")}});

  function showMessage(text,type="success"){message.textContent=text;message.className=`inline-message ${type}`}
  function clearMessage(){message.textContent="";message.className="inline-message hidden"}

  function saveForm(){
    const state={};
    [...form.elements].forEach(el=>{
      if(!el.name || el.type==="file") return;
      state[el.name]=el.type==="checkbox"?el.checked:el.value;
    });
    localStorage.setItem(STORAGE,JSON.stringify(state));
  }
  function restoreForm(){
    try{
      const state=JSON.parse(localStorage.getItem(STORAGE)||"null");
      if(!state)return;
      [...form.elements].forEach(el=>{
        if(!el.name || state[el.name]===undefined || el.type==="file")return;
        if(el.type==="checkbox")el.checked=!!state[el.name]; else el.value=state[el.name];
      });
    }catch(_){}
  }
  form.addEventListener("input",saveForm);form.addEventListener("change",saveForm);

  const allowed=/\.(pdf|png|jpe?g|webp|tif?f|dwg|dxf)$/i;
  function chooseFile(file){
    if(!file)return;
    if(!allowed.test(file.name)){modal("errorModal",t("invalidFile"));return}
    if(file.size>25*1024*1024){modal("errorModal",t("tooLarge"));return}
    selectedFile=file;renderFile(file);clearMessage();
  }
  function renderFile(file){
    filePreview.classList.remove("hidden");
    filePreview.innerHTML=`<div class="file-main"><span class="file-badge">PDF</span><div><strong>${escapeHtml(file.name)}</strong><div class="file-meta">${formatBytes(file.size)} · ${t("saved")}</div></div></div><button type="button" class="remove-file">Remove</button>`;
    filePreview.querySelector(".remove-file").addEventListener("click",e=>{
      e.stopPropagation();selectedFile=null;fileInput.value="";filePreview.classList.add("hidden");
    });
  }
  function formatBytes(n){return n<1024*1024?`${(n/1024).toFixed(0)} KB`:`${(n/1048576).toFixed(2)} MB`}
  function escapeHtml(v){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}

  browseBtn.addEventListener("click",e=>{e.preventDefault();e.stopPropagation();fileInput.click()});
  dropzone.addEventListener("click",e=>{if(e.target!==browseBtn && !e.target.closest(".remove-file"))fileInput.click()});
  dropzone.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();fileInput.click()}});
  fileInput.addEventListener("change",()=>chooseFile(fileInput.files[0]));
  ["dragenter","dragover"].forEach(ev=>dropzone.addEventListener(ev,e=>{e.preventDefault();dropzone.classList.add("drag")}));
  ["dragleave","drop"].forEach(ev=>dropzone.addEventListener(ev,e=>{e.preventDefault();dropzone.classList.remove("drag")}));
  dropzone.addEventListener("drop",e=>chooseFile(e.dataTransfer.files[0]));

  document.querySelectorAll(".nav-link").forEach(btn=>btn.addEventListener("click",()=>{
    document.querySelectorAll(".nav-link").forEach(x=>x.classList.remove("active"));btn.classList.add("active");
    if(btn.dataset.nav==="registration")document.querySelector(".submission-card").scrollIntoView({behavior:"smooth"});
    if(btn.dataset.nav==="records"){
      if(resultSection.classList.contains("hidden"))modal("errorModal","No 3D property record has been received yet. Submit a property first.");
      else resultSection.scrollIntoView({behavior:"smooth"});
    }
    if(btn.dataset.nav==="help")modal("helpModal");
  }));

  form.addEventListener("submit",async e=>{
    e.preventDefault();clearMessage();
    if(!form.reportValidity())return;
    const file=selectedFile||fileInput.files[0];
    if(!file){modal("errorModal",t("noBlueprint"));return}
    if(!cfg.SUBMIT_URL || /YOUR-BACKEND|localhost:8000/.test(cfg.SUBMIT_URL)){
      modal("errorModal",t("missingBackend"));return;
    }

    const fd=new FormData();
    // Explicit names keep the frontend/backend contract stable.
    ["ulpin","propertyName","propertyType","state","district","locality","surveyNumber","floors","area","address"].forEach(name=>{
      const el=form.elements[name]; if(el)fd.append(name,el.value);
    });
    fd.append("blueprint",file);
    fd.append("confirm","true");

    setLoading(true);
    try{
      const response=await fetch(cfg.SUBMIT_URL,{...(cfg.REQUEST||{}),method:"POST",body:fd});
      const text=await response.text();
      let data={};try{data=text?JSON.parse(text):{}}catch{data={message:text}}
      if(!response.ok)throw new Error(data.detail||data.message||`HTTP ${response.status}`);
      renderResult(data);
      resultSection.classList.remove("hidden");
      showMessage(t("success"),"success");
      resultSection.scrollIntoView({behavior:"smooth",block:"start"});
    }catch(err){
      modal("errorModal",`${t("submitFailed")} ${err.message||"Please check the API URL, CORS and backend endpoint."}`);
    }finally{setLoading(false)}
  });

  function setLoading(v){submitBtn.disabled=v;submitBtn.querySelector("span").textContent=v?"Submitting…":t("submit")}

  function renderResult(data){
    const p=data.property_details||data.property||data.details||{};
    const three=data.three_d_ulpin||data["3d_ulpin"]||data.ulpin_3d||data.generated_ulpin||data.threeDULPIN||"—";
    document.getElementById("resultUlpIn").textContent=three;
    const value=(keys, fallback="—")=>{
      for(const key of keys){if(p[key]!==undefined&&p[key]!==null&&p[key]!=="")return p[key]}
      for(const key of keys){const el=form.elements[key];if(el&&el.value)return el.value}
      return fallback;
    };
    const rows=[
      ["Property / Building",value(["propertyName","property_name"])],
      ["Property Type",value(["propertyType","property_type"])],
      ["2D ULPIN",value(["ulpin","parent_ulpin"])],
      ["State / UT",value(["state"])],["District",value(["district"])],
      ["Locality",value(["locality","village","ward"])],
      ["Survey / Plot No.",value(["surveyNumber","survey_number"])],
      ["Floors",value(["floors","number_of_floors"])],
      ["Parcel Area",value(["area","parcel_area"])],["Address",value(["address"])]
    ];
    document.getElementById("resultDetails").innerHTML=rows.map(([a,b])=>`<div class="detail"><span>${escapeHtml(a)}</span><strong>${escapeHtml(String(b))}</strong></div>`).join("");
    setupBlueprint(data.blueprint_url||data.blueprintUrl||data.blueprint||p.blueprint_url||"");
    setupModel(data.model_url||data.modelUrl||data.model||data.glb_url||data.glb||"");
  }
  function setupBlueprint(url){
    const img=document.getElementById("resultBlueprintImage"),pdf=document.getElementById("resultBlueprintPdf"),fallback=document.getElementById("blueprintFallback"),link=document.getElementById("blueprintLink");
    img.classList.add("hidden");pdf.classList.add("hidden");fallback.classList.remove("hidden");link.classList.add("hidden");
    if(!url)return; fallback.classList.add("hidden");link.href=url;link.classList.remove("hidden");
    const path=String(url).split("?")[0].toLowerCase();
    if(/\.(png|jpe?g|webp|tif?f)$/.test(path)){img.src=url;img.classList.remove("hidden")}
    else if(path.endsWith(".pdf")){pdf.src=url;pdf.classList.remove("hidden")}
  }
  function setupModel(url){
    const viewer=document.getElementById("modelViewer"),fallback=document.getElementById("modelFallback"),link=document.getElementById("modelLink");
    viewer.classList.add("hidden");fallback.classList.remove("hidden");link.classList.add("hidden");
    if(!url)return;viewer.src=url;viewer.classList.remove("hidden");fallback.classList.add("hidden");link.href=url;link.classList.remove("hidden");
  }

  document.getElementById("copyId").addEventListener("click",async()=>{
    const val=document.getElementById("resultUlpIn").textContent;if(!val||val==="—")return;
    try{await navigator.clipboard.writeText(val)}catch{window.prompt("Copy 3D ULPIN",val)}
    const btn=document.getElementById("copyId");btn.textContent=t("copied");setTimeout(()=>btn.textContent=t("copy"),1000);
  });
  document.getElementById("newSubmission").addEventListener("click",()=>{resultSection.classList.add("hidden");document.querySelector(".submission-card").scrollIntoView({behavior:"smooth"})});
  document.getElementById("resetBtn").addEventListener("click",()=>{
    form.reset();selectedFile=null;fileInput.value="";filePreview.classList.add("hidden");localStorage.removeItem(STORAGE);clearMessage();
  });
  languageSelect.value=localStorage.getItem(LANG)||"en";applyLanguage(languageSelect.value);languageSelect.addEventListener("change",()=>applyLanguage(languageSelect.value));
  restoreForm();
})();
