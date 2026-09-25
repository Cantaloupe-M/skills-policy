Finish the clinic intake summary `clinic_intake_template.hwpx` with the values in `patient_intake.json` and save the result to `/root/clinic_intake_ready.hwpx`.

Requirements:
- Replace every placeholder in the document, including repeated occurrences such as the patient-name confirmation line.
- Add an age note after the birth date using Korean full-year age as of the visit date, formatted as `(<N>세)`.
- Normalize the callback phone number to digits only with hyphen groups in `000-0000-0000` form.
- Keep the existing Korean labels and the handwritten-signature note.
- No `{{...}}` placeholder text may remain anywhere in the output.
- The result must remain a valid `.hwpx` package.
- Any paragraph whose text you modify must not retain stale layout-cache elements, so the edited document can open cleanly without overlapping characters.
