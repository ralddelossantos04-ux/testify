const gifs = {
default: document.getElementById("gif-default"),
student: document.getElementById("gif-student"),
teacher: document.getElementById("gif-teacher"),
admin: document.getElementById("gif-admin")
};

function restartGif(img){
const src = img.src;
img.src = "";
img.src = src;
}

function showGif(type){
Object.values(gifs).forEach(g => g.classList.remove("active"));

if(type !== "default"){
restartGif(gifs[type]);
}

gifs[type].classList.add("active");
}

document.querySelectorAll(".btn-role").forEach(btn=>{

btn.addEventListener("mouseenter",()=>{
showGif(btn.dataset.gif);
});

btn.addEventListener("mouseleave",()=>{
showGif("default");
});

btn.addEventListener("click", function(e){

const ripple = document.createElement("span");
const size = Math.max(this.offsetWidth,this.offsetHeight);
const rect = this.getBoundingClientRect();

ripple.className = "ripple";

ripple.style.cssText =
`width:${size}px;
height:${size}px;
left:${e.clientX - rect.left - size/2}px;
top:${e.clientY - rect.top - size/2}px`;

this.appendChild(ripple);

setTimeout(()=>ripple.remove(),600);

});

});

