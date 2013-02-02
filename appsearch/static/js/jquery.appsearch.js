// Depends on formset.js

(function($){
    $.fn.appsearch = function(opts){
        var options = $.extend({}, $.fn.appsearch.defaults, opts);
        var form = this;
        var _option_template = $("<option />")
        
        if (!options.modelSelect) {
            options.modelSelect = $("#model-select-wrapper select");
        }
        
        form.data('options', options);
        
        options.modelSelect.on('change.appsearch', function(){
            // Model has changed; trigger field list update
            var select = $(this);
            var value = select.val();
            if (value == '') {
                form.find('.constraint-form').slideUp('fast', function(){
                    $(this).find('.delete-row').click();
                })
            } else {
                form.trigger('update-field-list');
                form.trigger('configure-formset');
            }
        });
        form.find('.constraint-field select').on('change.appsearch', function(){
            // Field has changed; trigger operator list update for the target constraint
            var select = $(this);
            var option = select.find(':selected');
            var constraintForm = select.closest('.constraint-form');
            form.trigger('update-operator-list', [constraintForm]);
            
            // Set the description text
            var fieldType = option.attr('data-type');
            var fieldText = option.text();
            var fieldValue = option.val();
            var termInputs = constraintForm.find('.term input');
            var descriptionBox = constraintForm.find('.description');
            form.trigger('field-updated', [termInputs, fieldType, fieldText, fieldValue, constraintForm]);
            form.trigger('set-field-description', [descriptionBox, fieldType, fieldText, fieldValue, constraintForm]);
        });
        form.find('.constraint-operator select').on('change.appsearch', function(){
            var select = $(this);
            var option = select.find(':selected');
            var value = select.val();
            
            var constraintForm = select.closest('.constraint-form')
            var termInputs = constraintForm.find('.term');
            
            if (options.termlessOperators.indexOf(value) != -1) {
                // termless operator; hide inputs
                termInputs.slideUp('fast');
            } else {
                if (options.twoTermOperators.indexOf(value) != -1) {
                    // two-term operator; show both inputs
                    termInputs.slideDown('fast');
                } else {
                    // one-term operator; hide second input
                    termInputs.filter('.begin-term').slideDown('fast');
                    termInputs.filter('.end-term').slideUp('fast');
                }
            }
        });
        
        form.on('configure-formset.appsearch', function(){
            // Re-initialize the formset after stripping out the add/remove links
            form.find('.add-row,.delete-row').remove(); // formset.js
            form.find('.constraint-form').formset(options.formsetOptions); // formset.js
        });
        form.on('update-field-list.appsearch', function(e){
            // Default handler that tries to call a user-supplied function or else the default one
            (options.updateFieldList || function(){
                var modelValue = options.modelSelect.val();
                var choices = (options.getFields || $.fn.appsearch._getFields)(form, modelValue);
                
                // Remove all constraint forms but the first one.
                var constraintForms = form.find('.constraint-form');
                constraintForms.slice(1).slideUp('fast', function(){
                    $(this).find('.delete-row').click(); // formset.js
                });
                
                // 1 or 0 remaining constraint-form divs; make sure 1 exists
                var constraintForm = constraintForms.eq(0);
                if (constraintForm.size() == 0) {
                    form.find('.add-row').click(); // formset.js
                    constraintForm = form.find('.constraint-form');
                }
                        
                // Set the field <option> choices
                var fieldSelect = constraintForm.find('.constraint-field select');
                fieldSelect.empty();
                for (var i = 0; i < choices.length; i++) {
                    var info = choices[i];
                    var option = _option_template.clone().val(info[0]).text(info[1]);
                    option.attr('data-type', info[2]);
                    fieldSelect.append(option);
                }
                fieldSelect.change();
                
                // Ask for the operator list to update according to the form's field
                form.trigger('update-operator-list', [constraintForm]);
            })(e);
        });
        form.on('update-operator-list.appsearch', function(e, constraintForm){
            (options.updateOperatorList || function(e, constraintForm){
                var fieldSelect = constraintForm.find('.constraint-field select');
            
                var modelValue = options.modelSelect.val();
                var fieldValue = fieldSelect.val();
                var choices = (options.getOperators || $.fn.appsearch._getOperators)(form, modelValue, fieldValue);
            
                var operatorSelect = constraintForm.find('.constraint-operator select').empty();
                for (var i = 0; i < choices.length; i++) {
                    operatorSelect.append(_option_template.clone().val(choices[i]).text(choices[i]));
                }
                
                // Propagate change through the operator <select>, updating the term fields
                operatorSelect.change();
            })(e, constraintForm);
        });
        form.on('set-field-description.appsearch', function(e, descriptionBox, type, text, value, constraintForm){
            var f = options.setFieldDescription || $.fn.appsearch._setFieldDescription;
            f(descriptionBox, type, text, value, constraintForm);
        });
        
        // Make sure preloaded form data is immediately validated.
        form.trigger('configure-formset');
        
        // Make the form available for chained calls
        return this;
    };
    
    $.fn.appsearch._getFields = function(form, modelValue){
        var choices = form.data('options').formChoices;
        if (choices) {
            choices = choices.fields[modelValue];
        } else {
            console.error("No 'formChoices' object specified in appsearch options.  Supply the formChoices object during setup or supply a 'getFields' function in the setup options.");
        }
        return choices;
    };
    $.fn.appsearch._getOperators = function(form, modelValue, fieldValue){
        var choices = form.data('options').formChoices;
        if (choices) {
            choices = choices.operators[modelValue][fieldValue];
        } else {
            console.error("No 'formChoices' object specified in appsearch options.  Supply the formChoices object during setup or supply a 'getFields' function in the setup options.");
        }
        return choices;
    };
    $.fn.appsearch._setFieldDescription = function(descriptionBox, type, text, value, constraintForm) {
        var description;
        if (type == "text") {
            description = "Text";
        } else if (type == "date") {
            description = "Date";
        } else if (type == "number") {
            description = "Number";
        } else if (type == "boolean") {
            description = "true or false"
            // TODO: Change term input to <select> somewhere...
        } else {
            console.warn("Unknown field type:", type);
        }
                
        descriptionBox.text(description);
    };
    
    $.fn.appsearch.defaults = {
        'modelSelect': null,
        'formChoices': null,
        
        'modelSelectedCallback': null,
        'updateFieldList': null,
        'updateOperatorList': null,
        'constraintFormChanged': null,
        'setFieldDescription': null,
        
        'getFields': null,
        'getOperators': null,
        
        'termlessOperators': ["exists", "doesn't exist"],
        'twoTermOperators': ["between"],
        
        'formsetOptions': null,
    };
})(jQuery);
