// Listen for the file input change event and update the label accordingly
console.log("Hi")

document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('customFile').addEventListener('change', function (event) {
        // This will grab the file name

        var fileName = event.target.files[0].name;

        // Next, select the label that corresponds to the input and change its text to the file name
        var nextSibling = event.target.nextElementSibling;
        nextSibling.innerText = fileName;
    });
});