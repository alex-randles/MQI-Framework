function logout(event){
        var check = confirm("Do you really want to logout?");
        if(check){
           return true;
        }
        else {
            return false;
        }
}

function withdraw(event){
    var check = confirm("Do you really want to withdraw from the experiment?");
    if(check){
       return true;
    }
    else {
        return false;
    }
}

function disabledButton(event){
    var check = confirm("This button is disabled for the experiment!");
    return false;
}

//var source = new EventSource("/progress");
//source.onmessage = function(event) {
//    $('.progress-bar').css('width', event.data+'%').attr('aria-valuenow', event.data);
//    $('.progress-bar-label').text(event.data+'%');
//    if(event.data == 100){
//        source.close()
//    }
//}


function required()
{
    var name = document.forms["consent-form"]["name"].value;
    var checkbox = document.forms["consent-form"]["accept-form"].checked;
    var errMsgHolder = document.getElementById('nameErrMsg');
    if (name == "")
    {
            errMsgHolder.style.display = "block";
            errMsgHolder.innerHTML = "Please Enter your name!";
            event.preventDefault();
            return false;
    }
    else if (checkbox == false){
            errMsgHolder.style.display = "block";
            errMsgHolder.innerHTML = "Please Check the consent checkbox!";
            event.preventDefault();
            return false;
    }
    else
        {
            return true;
        }
}


function myFunction() {
  alert("Only RDF comments (rdfs:comment) will be in the refined mapping and not hash comments (#). Also the ordering of the triples could change as RDF graphs have no order.");
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
   if(e.style.display == 'block')
      e.style.display = 'none';
   else
      e.style.display = 'block';
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
    var id = setInterval(frame, 400);
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


function validateSourceDataForm() {
    var input_v1 = document.forms["sourceFileDetails"]["CSV_URL_1"].value;
    var input_v2 = document.forms["sourceFileDetails"]["CSV_URL_2"].value;
    var url_v1 = "https://raw.githubusercontent.com/kg-construct/rml-test-cases/master/test-cases/RMLTC0002a-CSV/student.csv";
    var url_v2 = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/manipulated_file/student.csv";
    var errMsgHolder = document.getElementById('nameErrMsg');
    if (input_v1 !== url_v1.trim()) {
          errMsgHolder.style.display = "block";
          errMsgHolder.innerHTML = "Version 1 URL incorrect.";
          alert("Version 1 URL incorrect.");
          return false;
    } else if (input_v2 !== url_v2.trim()) {
          errMsgHolder.style.display = "block";
          errMsgHolder.innerHTML = "Version 2 URL incorrect.";
          alert("Version 2 URL incorrect.");
          return false;
    } else {
         errMsgHolder.style.display = "none";
         move();
         return true;
    }
}

function scrollWin() {
  window.scrollBy(0, 100);
}

function addSampleSourceData(){
  document.getElementById('CSV_URL_1').value = "https://raw.githubusercontent.com/kg-construct/rml-test-cases/master/test-cases/RMLTC0002a-CSV/student.csv";
  document.getElementById('CSV_URL_2').value = "https://raw.githubusercontent.com/alex-randles/Change-Detection-System-Examples/main/manipulated_file/student.csv";
}

$('.collapse').collapse()

