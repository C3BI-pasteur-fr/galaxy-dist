(function(){var b=Handlebars.template,a=Handlebars.templates=Handlebars.templates||{};a.panel_section=b(function(e,k,d,j,i){this.compilerInfo=[4,">= 1.0.0"];d=this.merge(d,e.helpers);i=i||{};var g="",c,f="function",h=this.escapeExpression;g+='<div class="toolSectionTitle" id="title_';if(c=d.id){c=c.call(k,{hash:{},data:i})}else{c=k.id;c=typeof c===f?c.apply(k):c}g+=h(c)+'">\n    <a href="javascript:void(0)"><span>';if(c=d.name){c=c.call(k,{hash:{},data:i})}else{c=k.name;c=typeof c===f?c.apply(k):c}g+=h(c)+'</span></a>\n</div>\n<div id="';if(c=d.id){c=c.call(k,{hash:{},data:i})}else{c=k.id;c=typeof c===f?c.apply(k):c}g+=h(c)+'" class="toolSectionBody" style="display: none; ">\n    <div class="toolSectionBg"></div>\n<div>';return g})})();