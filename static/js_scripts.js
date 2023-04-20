function logout(event){
        var check = confirm("Do you really want to logout?");
        if(check){
           return true;
        }
        else {
            return false;
        }
}

function myFunction() {
  alert("Only RDF comments (rdfs:comment) will be in the refined mapping and not hash comments (#). Also the ordering of the triples could change as RDF graphs have no order.");
  return false;
}

function createPDF() {
    var sTable = document.getElementById('assessment-table').innerHTML
    var style = "<style>";
    style = style + "table {width: 100%;font: 17px Calibri;}";
    style = style + "table, th, td {border: solid 1px #DDD; border-collapse: collapse;";
    style = style + "padding: 2px 3px;text-align: center;}";
    style = style + "</style>";
    // CREATE A WINDOW OBJECT.
    var win = window.open('', '', 'height=700,width=700');
    win.document.write('<html><head>');
    win.document.write('<title>Profile</title>');   // <title> FOR PDF HEADER.
    win.document.write(style);          // ADD STYLE INSIDE THE HEAD TAG.
    win.document.write('</head>');
    win.document.write('<body>');
    win.document.write(sTable);         // THE TABLE CONTENTS INSIDE THE BODY TAG.
    win.document.write('</body></html>');
    win.document.close(); 	// CLOSE THE CURRENT WINDOW.
    win.print();    // PRINT THE CONTENTS.
    return false;
}


function showDiv(id){
   var e = document.getElementById(id);
   var button_text_id = 'button-' + id;
   if(e.style.display == 'block') {
      e.style.display = 'none';
      document.getElementById(button_text_id).innerText = 'Display Violation';
      document.getElementById(button_text_id).className = 'btn btn-secondary my-3';
   }
   else {
      e.style.display = 'block';
      document.getElementById(button_text_id).innerText = 'Hide Violation';
      document.getElementById(button_text_id).className = 'btn btn-primary my-3';
   }
}


function showDivInLine(id){
   var e = document.getElementById(id);
   if(e.style.display == 'block')
      e.style.display = 'none';
   else
      e.style.display = 'inline-block';
}


function hideInfoButtons() {
    var divsToHide = document.getElementsByClassName("info-button"); //divsToHide is an array
    for(var i = 0; i < divsToHide.length; i++){
        divsToHide[i].style.visibility = "hidden"; // or
        divsToHide[i].style.display = "none"; // depending on what you're doing
    }
}


function changeIcon(div_id){
    var icon_id = "icon-" + div_id;
    var className = document.getElementById(icon_id).className;
    if (className == "bi bi-plus-circle px-3")
        document.getElementById(icon_id).className =  "bi bi-dash-circle px-3" ;
    else
        document.getElementById(icon_id).className = "bi bi-plus-circle px-3";
}


function scroll() {
  const element = document.getElementById("footer");
  element.scrollIntoView();
}


function move() {
var i = 0;
  if (i == 0) {
    i = 1;
    var elem = document.getElementById("myBar");
    var width = 1;
    var id = setInterval(frame, 800);
    function frame() {
      if (width >= 100) {
       //  clearInterval(id);
        move();
        i = 0;
      } else {
        width++;
        elem.style.width = width + "%";
      }
    }
  }
}

function validateMappingForm() {
    var errMsgHolder = document.getElementById('nameErrMsg');
    var mapping_file = document.forms["mappingUpload"]["mappingFile"].value;
    var errMsgHolder = document.getElementById('nameErrMsg');
    if (mapping_file.trim().endsWith('ttl') == false) {
          errMsgHolder.style.display = "block";
          errMsgHolder.innerHTML = "Mapping File must be turtle format (.ttl)";
          return false;
    } else {
         move();
         return true;
    }
}

function scrollWin() {
  window.scrollBy(0, 100);
}

function addSampleSourceData(sample_data_identifier){
  if (sample_data_identifier == 0){
      document.getElementById('CSV_URL_1').value = "";
      document.getElementById('CSV-URL-2').value = "";
  }
  else if (sample_data_identifier == 1){
      document.getElementById('CSV-URL-1').value = "https://raw.githubusercontent.com/kg-construct/rml-test-cases/master/test-cases/RMLTC0002a-CSV/student.csv";
      document.getElementById('CSV-URL-2').value = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/manipulated_file/student-v3.csv";
  }
  else if (sample_data_identifier == 2){
     document.getElementById('CSV-URL-1').value = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_1_files/products.csv";
     document.getElementById('CSV-URL-2').value = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_2_files/products.csv";
  }
  else if (sample_data_identifier == 3){
     document.getElementById('CSV-URL-1').value = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_1_files/employee.csv";
     document.getElementById('CSV-URL-2').value = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_2_files/employee.csv";
  }
  else if (sample_data_identifier == 4){
     document.getElementById('CSV-URL-1').value = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_1_files/loans-v1.csv";
     document.getElementById('CSV-URL-2').value = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/version_2_files/loans-v1.csv";
  }
}

// validate not all refinements are manual
function validateRefinementSelection() {
    var inputs = document.getElementById("refinement-selection").elements;
    var all_manual_refinements = true;
    for (var i = 0; i < inputs.length; i++) {
        if (inputs[i].nodeName == "SELECT"){
           var value = inputs[i].value.toLocaleUpperCase();
           if (value != "MANUAL"){
                   all_manual_refinements = false;
           }
        }
    }
    if (all_manual_refinements == true){
       document.getElementById('manual-refinements-warning').style.display = "block";
       return false;
    }
    else {
       return true;
    }
}

function selectAllRefinements() {
    var allInputs = document.getElementsByTagName("input");
    for (var i = 0, max = allInputs.length; i < max; i++){
        if (allInputs[i].type === 'checkbox') {
            var checkBoxStatus = allInputs[i].checked;
            if (checkBoxStatus == true){
                 allInputs[i].checked = false;
            }
            else {
                 allInputs[i].checked = true;
            }
         }
    }
}


$('.collapse').collapse()

